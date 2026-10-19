package ru.shipokhvat.listener;

import org.bukkit.Location;
import org.bukkit.entity.EnderPearl;
import org.bukkit.entity.LivingEntity;
import org.bukkit.entity.Player;
import org.bukkit.event.EventHandler;
import org.bukkit.event.EventPriority;
import org.bukkit.event.Listener;
import org.bukkit.event.block.Action;
import org.bukkit.event.entity.EntityDamageByEntityEvent;
import org.bukkit.event.entity.EntityDamageEvent;
import org.bukkit.event.entity.EntityDeathEvent;
import org.bukkit.event.player.PlayerInteractEvent;
import org.bukkit.event.player.PlayerItemHeldEvent;
import org.bukkit.event.player.PlayerJoinEvent;
import org.bukkit.event.player.PlayerMoveEvent;
import org.bukkit.event.player.PlayerQuitEvent;
import org.bukkit.event.player.PlayerTeleportEvent;
import org.bukkit.inventory.EquipmentSlot;
import ru.shipokhvat.Settings;
import ru.shipokhvat.ShipokhvatPlugin;
import ru.shipokhvat.util.Text;

import java.util.HashMap;
import java.util.Map;
import java.util.UUID;

public final class WeaponListener implements Listener {

    private final ShipokhvatPlugin plugin;
    /** Защита от двойного срабатывания ПКМ (по блоку и по воздуху в один тик). */
    private final Map<UUID, Long> lastUse = new HashMap<>();

    public WeaponListener(ShipokhvatPlugin plugin) {
        this.plugin = plugin;
    }

    // ---------------------------------------------------------------- ПКМ

    @EventHandler(priority = EventPriority.HIGH)
    public void onInteract(PlayerInteractEvent e) {
        if (e.getHand() != EquipmentSlot.HAND) return;
        Action a = e.getAction();
        if (a != Action.RIGHT_CLICK_AIR && a != Action.RIGHT_CLICK_BLOCK) return;
        Player p = e.getPlayer();
        if (!plugin.weapon().isHolding(p)) return;
        // Обычный ПКМ по сундуку/двери — открываем блок, а не способность.
        if (a == Action.RIGHT_CLICK_BLOCK && !p.isSneaking()
                && e.getClickedBlock() != null && e.getClickedBlock().getType().isInteractable()) return;

        long now = System.currentTimeMillis();
        Long last = lastUse.put(p.getUniqueId(), now);
        if (last != null && now - last < 150) return;

        if (p.isSneaking()) plugin.pull().tryActivate(p);
        else plugin.root().tryArm(p);
    }

    // ---------------------------------------------------------------- удар

    @EventHandler(priority = EventPriority.HIGHEST, ignoreCancelled = true)
    public void onHit(EntityDamageByEntityEvent e) {
        if (e.getCause() != EntityDamageEvent.DamageCause.ENTITY_ATTACK) return;
        if (!(e.getDamager() instanceof Player p) || !(e.getEntity() instanceof LivingEntity victim)) return;
        if (victim == p || !plugin.weapon().isHolding(p)) return;
        plugin.root().onHit(p, victim);
    }

    // ---------------------------------------------------------------- удержание

    @EventHandler(priority = EventPriority.HIGHEST, ignoreCancelled = true)
    public void onMove(PlayerMoveEvent e) {
        Location lock = plugin.root().lockOf(e.getPlayer().getUniqueId());
        if (lock == null) return;
        Location to = e.getTo();
        boolean lockRot = plugin.settings().rootLockRotation;
        boolean moved = Math.abs(to.getX() - lock.getX()) > 1e-4
                || Math.abs(to.getY() - lock.getY()) > 1e-4
                || Math.abs(to.getZ() - lock.getZ()) > 1e-4;
        boolean turned = lockRot && (Math.abs(Location.normalizeYaw(to.getYaw() - lock.getYaw())) > 0.01
                || Math.abs(to.getPitch() - lock.getPitch()) > 0.01);
        if (!moved && !turned) return;
        Location fixed = lock.clone();
        if (!lockRot) {
            fixed.setYaw(to.getYaw());
            fixed.setPitch(to.getPitch());
        }
        e.setTo(fixed);
    }

    @EventHandler(priority = EventPriority.HIGH, ignoreCancelled = true)
    public void onTeleport(PlayerTeleportEvent e) {
        if (plugin.root().lockOf(e.getPlayer().getUniqueId()) == null) return;
        if (!plugin.settings().rootBlockedTeleports.contains(e.getCause().name())) return;
        e.setCancelled(true);
        Text.send(e.getPlayer(), "teleport-blocked");
    }

    @EventHandler(priority = EventPriority.HIGH, ignoreCancelled = true)
    public void onPearl(com.destroystokyo.paper.event.player.PlayerLaunchProjectileEvent e) {
        Settings s = plugin.settings();
        if (!s.rootBlockPearls || !(e.getProjectile() instanceof EnderPearl)) return;
        if (plugin.root().lockOf(e.getPlayer().getUniqueId()) == null) return;
        e.setShouldConsume(false);
        e.setCancelled(true);
        Text.send(e.getPlayer(), "pearl-blocked");
    }

    // ---------------------------------------------------------------- служебное

    @EventHandler
    public void onJoin(PlayerJoinEvent e) {
        plugin.weapon().refreshInventory(e.getPlayer());
    }

    @EventHandler
    public void onHeld(PlayerItemHeldEvent e) {
        Player p = e.getPlayer();
        plugin.getServer().getScheduler().runTask(plugin, () -> plugin.weapon().refreshMainHand(p));
    }

    @EventHandler
    public void onQuit(PlayerQuitEvent e) {
        plugin.root().clearPlayer(e.getPlayer());
        plugin.pull().cancel(e.getPlayer());
        lastUse.remove(e.getPlayer().getUniqueId());
    }

    @EventHandler
    public void onDeath(EntityDeathEvent e) {
        if (e.getEntity() instanceof Player p) {
            plugin.root().clearPlayer(p);
            plugin.pull().cancel(p);
        }
    }
}
