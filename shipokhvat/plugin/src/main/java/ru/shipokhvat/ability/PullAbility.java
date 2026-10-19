package ru.shipokhvat.ability;

import org.bukkit.Color;
import org.bukkit.FluidCollisionMode;
import org.bukkit.GameMode;
import org.bukkit.Location;
import org.bukkit.Particle;
import org.bukkit.damage.DamageSource;
import org.bukkit.damage.DamageType;
import org.bukkit.entity.ArmorStand;
import org.bukkit.entity.BlockDisplay;
import org.bukkit.entity.Display;
import org.bukkit.entity.Entity;
import org.bukkit.entity.LivingEntity;
import org.bukkit.entity.Mob;
import org.bukkit.entity.Player;
import org.bukkit.scheduler.BukkitRunnable;
import org.bukkit.util.RayTraceResult;
import org.bukkit.util.Transformation;
import org.bukkit.util.Vector;
import org.joml.Quaternionf;
import org.joml.Vector3f;
import ru.shipokhvat.Settings;
import ru.shipokhvat.ShipokhvatPlugin;
import ru.shipokhvat.util.Text;

import java.util.HashMap;
import java.util.Map;
import java.util.UUID;

/**
 * Способность 2 «Притягивание»: Shift+ПКМ выпускает лозу,
 * она летит к цели, наносит урон сквозь броню и подтягивает цель к владельцу.
 */
public final class PullAbility {

    private static final Particle.DustOptions VINE_DUST = new Particle.DustOptions(Color.fromRGB(0x4E8A2E), 0.9f);

    private final ShipokhvatPlugin plugin;
    private final Cooldowns cooldowns = new Cooldowns();
    private final Map<UUID, VineTask> active = new HashMap<>();

    public PullAbility(ShipokhvatPlugin plugin) {
        this.plugin = plugin;
    }

    public Cooldowns cooldowns() {
        return cooldowns;
    }

    public void tryActivate(Player player) {
        Settings s = plugin.settings();
        if (!s.pullEnabled) {
            Text.send(player, "ability-disabled");
            return;
        }
        if (active.containsKey(player.getUniqueId())) return;
        double left = cooldowns.remaining(player);
        if (left > 0) {
            Text.send(player, "on-cooldown", "ability", s.message("pull-name"), "time", Cooldowns.format(left));
            return;
        }

        Location eye = player.getEyeLocation();
        Vector dir = eye.getDirection();
        RayTraceResult hit = player.getWorld().rayTrace(eye, dir, s.pullRange, FluidCollisionMode.NEVER,
                true, 0.35, e -> isTarget(player, e, s));

        LivingEntity target = hit != null && hit.getHitEntity() instanceof LivingEntity le ? le : null;
        Location missPoint = hit != null ? hit.getHitPosition().toLocation(player.getWorld())
                : eye.clone().add(dir.clone().multiply(s.pullRange));

        cooldowns.set(player, target != null ? s.pullCooldown : s.pullMissCooldown);
        Text.sound(player.getLocation(), s.soundPullShoot, 1f, 0.6f);

        VineTask task = new VineTask(player, target, missPoint);
        active.put(player.getUniqueId(), task);
        task.runTaskTimer(plugin, 0L, 1L);
    }

    public void cancelAll() {
        for (VineTask t : active.values().toArray(new VineTask[0])) t.finish();
        active.clear();
    }

    public void cancel(Player player) {
        VineTask t = active.get(player.getUniqueId());
        if (t != null) t.finish();
    }

    private boolean isTarget(Player owner, Entity e, Settings s) {
        if (e == owner || !(e instanceof LivingEntity) || e.isDead()) return false;
        if (e instanceof Player p) {
            return p.getGameMode() != GameMode.SPECTATOR && p.getGameMode() != GameMode.CREATIVE;
        }
        return s.pullAffectMobs && e instanceof Mob && !(e instanceof ArmorStand);
    }

    /**
     * Наносит урон от владельца. Возвращает false, если урон заблокирован
     * (PvP выключен, регион, бессмертие) — тогда цель не притягиваем.
     */
    private boolean dealDamage(Player owner, LivingEntity target, Settings s) {
        double amount = s.pullDamageHearts * 2;
        if (amount <= 0) return true;
        DamageSource src = DamageSource.builder(DamageType.MAGIC)
                .withCausingEntity(owner).withDirectEntity(owner).build();
        double before = target.getHealth() + target.getAbsorptionAmount();
        target.setNoDamageTicks(0);
        target.damage(amount, src);
        if (target.isDead()) return true;
        double dealt = before - (target.getHealth() + target.getAbsorptionAmount());
        if (dealt <= 0.0001) return false;

        if (s.pullTrueDamage && dealt < amount) {
            // Добиваем то, что срезали броня/зачарования/сопротивление.
            double rest = amount - dealt;
            double abs = target.getAbsorptionAmount();
            double fromAbs = Math.min(abs, rest);
            target.setAbsorptionAmount(abs - fromAbs);
            rest -= fromAbs;
            if (rest > 0) {
                double hp = target.getHealth() - rest;
                if (hp <= 0) target.damage(Float.MAX_VALUE, src);
                else target.setHealth(hp);
            }
        }
        // Не сбиваем владельцу комбо: сразу после лозы можно бить мечом.
        target.setNoDamageTicks(0);
        return true;
    }

    // ------------------------------------------------------------------------

    private enum Phase { EXTEND, PULL, RETRACT }

    private final class VineTask extends BukkitRunnable {
        final Player owner;
        final LivingEntity target;
        final Location missPoint;
        final BlockDisplay vine;
        Phase phase = Phase.EXTEND;
        double length = 0;
        double retractFrom;
        int pullTicks = 0;
        boolean finished;

        VineTask(Player owner, LivingEntity target, Location missPoint) {
            this.owner = owner;
            this.target = target;
            this.missPoint = missPoint;
            Settings s = plugin.settings();
            Location start = handPos();
            start.setYaw(0);
            start.setPitch(0);
            this.vine = owner.getWorld().spawn(start, BlockDisplay.class, d -> {
                d.setPersistent(false);
                d.setBlock(s.pullVineBlock.createBlockData());
                d.setBillboard(Display.Billboard.FIXED);
                d.setTeleportDuration(1);
                d.setTransformation(new Transformation(new Vector3f(), new Quaternionf(),
                        new Vector3f(0, 0, 0), new Quaternionf()));
            });
        }

        Location handPos() {
            Location eye = owner.getEyeLocation();
            Vector dir = eye.getDirection();
            Vector right = dir.clone().crossProduct(new Vector(0, 1, 0));
            if (right.lengthSquared() < 1e-6) right = new Vector(1, 0, 0);
            right.normalize().multiply(0.35);
            return eye.add(right).add(0, -0.45, 0).add(dir.multiply(0.3));
        }

        Location endPoint() {
            if (target != null) return target.getLocation().add(0, target.getHeight() * 0.55, 0);
            return missPoint;
        }

        @Override
        public void run() {
            Settings s = plugin.settings();
            if (!owner.isOnline() || owner.isDead()
                    || (target != null && (!target.isValid() || target.getWorld() != owner.getWorld()))) {
                finish();
                return;
            }
            Location start = handPos();
            Location end = endPoint();
            double dist = start.distance(end);

            switch (phase) {
                case EXTEND -> {
                    length = Math.min(dist, length + s.pullVineSpeed);
                    if (target != null && dist > s.pullRange + 6) {
                        startRetract();
                    } else if (length >= dist) {
                        if (target == null) {
                            Text.sound(end, s.soundPullMiss, 1f, 1.2f);
                            Text.send(owner, "pull-miss");
                            startRetract();
                        } else {
                            onReach(s);
                        }
                    }
                }
                case PULL -> {
                    length = dist;
                    pullTicks++;
                    Vector to = owner.getLocation().toVector().subtract(target.getLocation().toVector());
                    if (to.length() <= s.pullStopDistance || pullTicks > s.pullMaxTicks) {
                        target.setVelocity(target.getVelocity().multiply(0.2));
                        target.setFallDistance(0);
                        startRetract();
                    } else {
                        Vector v = to.normalize().multiply(s.pullSpeed);
                        if (target.isOnGround()) v.setY(Math.max(v.getY(), 0.25));
                        target.setVelocity(v);
                        target.setFallDistance(0);
                    }
                }
                case RETRACT -> {
                    length -= s.pullVineSpeed * 1.5;
                    if (length <= 0.05) {
                        finish();
                        return;
                    }
                }
            }
            draw(start, end, Math.min(length, dist), s);
        }

        void onReach(Settings s) {
            Location at = target.getLocation().add(0, 1, 0);
            if (!dealDamage(owner, target, s)) {
                Text.send(owner, "pull-protected");
                startRetract();
                return;
            }
            Text.sound(at, s.soundPullHit, 1.2f, 0.8f);
            Text.sound(at, s.soundPullHit2, 0.8f, 1.1f);
            target.getWorld().spawnParticle(Particle.BLOCK, at, 25, 0.3, 0.4, 0.3,
                    s.pullVineBlock.createBlockData());
            Text.send(owner, "pull-hit", "target", target.getName());
            if (target instanceof Player p) Text.send(p, "pull-victim");

            if (target.isDead() || plugin.root().isRooted(target)) {
                startRetract();
                return;
            }
            Text.sound(owner.getLocation(), s.soundPullPull, 1f, 1.2f);
            phase = Phase.PULL;
        }

        void startRetract() {
            phase = Phase.RETRACT;
            retractFrom = length;
        }

        void draw(Location start, Location end, double len, Settings s) {
            if (!vine.isValid()) return;
            Vector full = end.toVector().subtract(start.toVector());
            if (full.lengthSquared() < 1e-6) return;
            Vector3f dir = new Vector3f((float) full.getX(), (float) full.getY(), (float) full.getZ()).normalize();
            float w = s.pullVineWidth;
            Quaternionf rot = new Quaternionf().rotationTo(new Vector3f(0, 0, 1), dir);
            Vector3f translation = rot.transform(new Vector3f(-w / 2, -w / 2, 0));

            Location at = start.clone();
            at.setYaw(0);
            at.setPitch(0);
            vine.teleport(at);
            vine.setInterpolationDelay(0);
            vine.setInterpolationDuration(1);
            vine.setTransformation(new Transformation(translation, rot,
                    new Vector3f(w, w, (float) len), new Quaternionf()));

            if (s.pullParticles) {
                Vector step = full.clone().normalize();
                for (double d = 0.5; d < len; d += 0.6) {
                    Location p = start.clone().add(step.clone().multiply(d));
                    owner.getWorld().spawnParticle(Particle.DUST, p, 1, 0.05, 0.05, 0.05, 0, VINE_DUST);
                }
                Location tip = start.clone().add(step.multiply(len));
                owner.getWorld().spawnParticle(Particle.BLOCK, tip, 2, 0.05, 0.05, 0.05,
                        s.pullVineBlock.createBlockData());
            }
        }

        void finish() {
            if (finished) return;
            finished = true;
            if (vine.isValid()) vine.remove();
            active.remove(owner.getUniqueId(), this);
            cancel();
        }
    }
}
