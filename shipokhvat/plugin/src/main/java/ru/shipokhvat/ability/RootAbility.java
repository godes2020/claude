package ru.shipokhvat.ability;

import org.bukkit.FluidCollisionMode;
import org.bukkit.Location;
import org.bukkit.Material;
import org.bukkit.NamespacedKey;
import org.bukkit.Particle;
import org.bukkit.attribute.Attribute;
import org.bukkit.attribute.AttributeInstance;
import org.bukkit.attribute.AttributeModifier;
import org.bukkit.entity.BlockDisplay;
import org.bukkit.entity.Display;
import org.bukkit.entity.LivingEntity;
import org.bukkit.entity.Mob;
import org.bukkit.entity.Player;
import org.bukkit.util.RayTraceResult;
import org.bukkit.util.Transformation;
import org.bukkit.util.Vector;
import org.joml.Quaternionf;
import org.joml.Vector3f;
import ru.shipokhvat.Settings;
import ru.shipokhvat.ShipokhvatPlugin;
import ru.shipokhvat.util.Text;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.Iterator;
import java.util.List;
import java.util.Map;
import java.util.UUID;

/**
 * Способность 1 «Хватка лозы»: ПКМ заряжает следующий удар,
 * удар опутывает цель лозой — нельзя двигаться, поворачиваться и телепортироваться.
 */
public final class RootAbility {

    private final ShipokhvatPlugin plugin;
    private final Cooldowns cooldowns = new Cooldowns();
    private final NamespacedKey speedKey;
    private final NamespacedKey jumpKey;

    /** Игрок → момент, когда заряд пропадёт. */
    private final Map<UUID, Long> armed = new HashMap<>();
    /** Опутанная цель → данные. */
    private final Map<UUID, Root> roots = new HashMap<>();

    private static final class Root {
        final LivingEntity entity;
        final Location lock;
        final long endMillis;
        final List<BlockDisplay> displays = new ArrayList<>();
        Boolean wasAware;

        Root(LivingEntity entity, Location lock, long endMillis) {
            this.entity = entity;
            this.lock = lock;
            this.endMillis = endMillis;
        }
    }

    public RootAbility(ShipokhvatPlugin plugin) {
        this.plugin = plugin;
        this.speedKey = new NamespacedKey(plugin, "root_speed");
        this.jumpKey = new NamespacedKey(plugin, "root_jump");
    }

    public Cooldowns cooldowns() {
        return cooldowns;
    }

    public boolean isArmed(Player player) {
        return armed.containsKey(player.getUniqueId());
    }

    // ---------------------------------------------------------------- активация

    public void tryArm(Player player) {
        Settings s = plugin.settings();
        if (!s.rootEnabled) {
            Text.send(player, "ability-disabled");
            return;
        }
        if (isArmed(player)) {
            Text.send(player, "root-already-armed");
            return;
        }
        double left = cooldowns.remaining(player);
        if (left > 0) {
            Text.send(player, "on-cooldown", "ability", s.message("root-name"), "time", Cooldowns.format(left));
            return;
        }
        long until = s.rootArmTimeout <= 0 ? Long.MAX_VALUE
                : System.currentTimeMillis() + (long) (s.rootArmTimeout * 1000);
        armed.put(player.getUniqueId(), until);
        if (s.rootCooldownOnActivate) cooldowns.set(player, s.rootCooldown);

        Text.send(player, "root-armed");
        Text.sound(player.getLocation(), s.soundRootArm, 1f, 0.7f);
        player.getWorld().spawnParticle(Particle.HAPPY_VILLAGER,
                player.getLocation().add(0, 1, 0), 15, 0.4, 0.5, 0.4, 0);
    }

    /** Вызывается при ударе мечом. true — цель опутана. */
    public boolean onHit(Player attacker, LivingEntity victim) {
        Settings s = plugin.settings();
        if (!isArmed(attacker) || !s.rootEnabled) return false;
        if (victim instanceof Player p) {
            if (p.getGameMode() == org.bukkit.GameMode.SPECTATOR || p.getGameMode() == org.bukkit.GameMode.CREATIVE) return false;
        } else if (!s.rootAffectMobs || !(victim instanceof Mob)) {
            return false;
        }
        armed.remove(attacker.getUniqueId());
        if (!s.rootCooldownOnActivate) cooldowns.set(attacker, s.rootCooldown);
        apply(victim);
        Text.send(attacker, "root-hit", "target", victim.getName());
        return true;
    }

    // ---------------------------------------------------------------- состояние

    public boolean isRooted(LivingEntity entity) {
        return roots.containsKey(entity.getUniqueId());
    }

    /** Точка, в которой зафиксирована цель, или null. */
    public Location lockOf(UUID id) {
        Root r = roots.get(id);
        return r == null ? null : r.lock;
    }

    public void clearPlayer(Player player) {
        armed.remove(player.getUniqueId());
        release(player.getUniqueId(), false);
    }

    public void releaseAll() {
        for (UUID id : new ArrayList<>(roots.keySet())) release(id, false);
        armed.clear();
    }

    // ---------------------------------------------------------------- логика

    private void apply(LivingEntity target) {
        Settings s = plugin.settings();
        release(target.getUniqueId(), false); // повторное попадание — обновляем

        Location lock = target.getLocation().clone();
        if (s.rootSnapToGround > 0 && !target.isOnGround()) {
            RayTraceResult hit = target.getWorld().rayTraceBlocks(lock, new Vector(0, -1, 0),
                    s.rootSnapToGround, FluidCollisionMode.NEVER, true);
            if (hit != null) lock.setY(hit.getHitPosition().getY());
        }
        target.teleport(lock);
        target.setVelocity(new Vector());

        Root root = new Root(target, lock, System.currentTimeMillis() + (long) (s.rootDuration * 1000));
        roots.put(target.getUniqueId(), root);

        addModifier(target, Attribute.MOVEMENT_SPEED, speedKey);
        addModifier(target, Attribute.JUMP_STRENGTH, jumpKey);
        if (target instanceof Mob mob) {
            root.wasAware = mob.isAware();
            mob.setAware(false);
        }

        spawnVisual(root, s);
        Text.sound(lock, s.soundRootHit, 1.2f, 0.8f);
        Text.sound(lock, s.soundRootHit2, 0.7f, 1.3f);
        target.getWorld().spawnParticle(Particle.BLOCK, lock.clone().add(0, 0.2, 0), 40, 0.5, 0.1, 0.5,
                Material.ROOTED_DIRT.createBlockData());
        if (target instanceof Player p) Text.send(p, "root-victim");
    }

    private void release(UUID id, boolean notify) {
        Root root = roots.remove(id);
        if (root == null) return;
        LivingEntity e = root.entity;
        removeModifier(e, Attribute.MOVEMENT_SPEED, speedKey);
        removeModifier(e, Attribute.JUMP_STRENGTH, jumpKey);
        if (e instanceof Mob mob && root.wasAware != null && mob.isValid()) mob.setAware(root.wasAware);
        for (BlockDisplay d : root.displays) d.remove();
        if (notify && e.isValid()) {
            Settings s = plugin.settings();
            Text.sound(e.getLocation(), s.soundRootRelease, 1f, 1f);
            e.getWorld().spawnParticle(Particle.BLOCK, e.getLocation().add(0, 1, 0), 30, 0.4, 0.6, 0.4,
                    Material.MOSS_BLOCK.createBlockData());
            if (e instanceof Player p) Text.send(p, "root-released");
        }
    }

    /** Каждый тик. */
    public void tick() {
        long now = System.currentTimeMillis();

        Iterator<Map.Entry<UUID, Long>> it = armed.entrySet().iterator();
        while (it.hasNext()) {
            Map.Entry<UUID, Long> en = it.next();
            if (now < en.getValue()) continue;
            it.remove();
            Player p = plugin.getServer().getPlayer(en.getKey());
            if (p != null) Text.send(p, "root-expired");
        }

        for (Root root : new ArrayList<>(roots.values())) {
            LivingEntity e = root.entity;
            if (!e.isValid() || e.isDead() || e.getWorld() != root.lock.getWorld()) {
                release(e.getUniqueId(), false);
                continue;
            }
            if (now >= root.endMillis) {
                release(e.getUniqueId(), true);
                continue;
            }
            // Игроков держит PlayerMoveEvent, мобов — телепорт обратно.
            if (!(e instanceof Player)) {
                if (e.getLocation().distanceSquared(root.lock) > 0.0004) e.teleport(root.lock);
                e.setVelocity(new Vector());
            }
            if (now % 500 < 50) {
                e.getWorld().spawnParticle(Particle.BLOCK, root.lock.clone().add(0, 0.8, 0), 4, 0.35, 0.5, 0.35,
                        Material.MOSS_BLOCK.createBlockData());
            }
        }
    }

    // ---------------------------------------------------------------- визуал

    private void spawnVisual(Root root, Settings s) {
        Location base = root.lock.clone();
        base.setYaw(0);
        base.setPitch(0);
        float r = (float) s.rootRadius;
        float w = 0.7f;

        for (int i = 0; i < s.rootStalkCount && !s.rootStalkBlocks.isEmpty(); i++) {
            Material m = s.rootStalkBlocks.get(i % s.rootStalkBlocks.size());
            double a = Math.PI * 2 * i / s.rootStalkCount + Math.random() * 0.3;
            float ox = (float) (Math.cos(a) * r);
            float oz = (float) (Math.sin(a) * r);
            // Поворачиваем стебель лицом к цели и наклоняем верхушку к ней.
            float face = (float) Math.atan2(-Math.cos(a), -Math.sin(a));
            Quaternionf rot = new Quaternionf().rotateY(face).rotateX(0.22f + (float) Math.random() * 0.12f);
            Vector3f t = rot.transform(new Vector3f(-w / 2, 0, -w / 2)).add(ox, 0, oz);
            float h = s.rootStalkHeight * (0.8f + (float) Math.random() * 0.3f);
            spawnGrowing(root, base, m, t, rot, new Vector3f(w, 0.01f, w), new Vector3f(w, h, w), s.rootGrowTicks);
        }
        if (s.rootWebBlock != null) {
            float ws = s.rootWebScale;
            Vector3f t = new Vector3f(-ws / 2, 0.25f, -ws / 2);
            spawnGrowing(root, base, s.rootWebBlock, t, new Quaternionf(),
                    new Vector3f(ws, 0.01f, ws), new Vector3f(ws, ws, ws), s.rootGrowTicks + 2);
        }
        if (s.rootGroundBlock != null) {
            Vector3f t = new Vector3f(-0.05f, 0.001f, -0.05f);
            spawnGrowing(root, base, s.rootGroundBlock, t, new Quaternionf(),
                    new Vector3f(0.1f, 1f, 0.1f), new Vector3f(2f, 1f, 2f), Math.max(1, s.rootGrowTicks / 2));
        }
    }

    private void spawnGrowing(Root root, Location at, Material block, Vector3f translation, Quaternionf rotation,
                              Vector3f fromScale, Vector3f toScale, int ticks) {
        if (!block.isBlock()) return;
        BlockDisplay d = at.getWorld().spawn(at, BlockDisplay.class, disp -> {
            disp.setPersistent(false);
            disp.setBlock(block.createBlockData());
            disp.setBillboard(Display.Billboard.FIXED);
            disp.setTransformation(new Transformation(new Vector3f(translation), new Quaternionf(rotation),
                    new Vector3f(fromScale), new Quaternionf()));
        });
        root.displays.add(d);
        // Интерполяция срабатывает только если трансформацию поменять после спавна.
        plugin.getServer().getScheduler().runTaskLater(plugin, () -> {
            if (!d.isValid()) return;
            Vector3f t = new Vector3f(translation);
            // Для растущих по горизонтали блоков (подстилка) центрируем заново
            if (fromScale.x != toScale.x) t.set(-toScale.x / 2, translation.y, -toScale.z / 2);
            d.setInterpolationDelay(0);
            d.setInterpolationDuration(ticks);
            d.setTransformation(new Transformation(t, new Quaternionf(rotation), new Vector3f(toScale), new Quaternionf()));
        }, 2L);
    }

    // ---------------------------------------------------------------- атрибуты

    private static void addModifier(LivingEntity e, Attribute attr, NamespacedKey key) {
        AttributeInstance inst = e.getAttribute(attr);
        if (inst == null) return;
        inst.removeModifier(key);
        // transient — не сохраняется в файл игрока, даже если сервер упадёт
        inst.addTransientModifier(new AttributeModifier(key, -1, AttributeModifier.Operation.MULTIPLY_SCALAR_1));
    }

    private static void removeModifier(LivingEntity e, Attribute attr, NamespacedKey key) {
        AttributeInstance inst = e.getAttribute(attr);
        if (inst != null) inst.removeModifier(key);
    }
}
