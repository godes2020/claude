package ru.shipokhvat.ability;

import org.bukkit.entity.Player;

import java.util.HashMap;
import java.util.Map;
import java.util.UUID;

/** Перезарядка одной способности, привязана к игроку (а не к предмету). */
public final class Cooldowns {

    private final Map<UUID, Long> until = new HashMap<>();

    public void set(Player player, double seconds) {
        if (seconds <= 0 || player.hasPermission("shipokhvat.bypasscooldown")) {
            until.remove(player.getUniqueId());
            return;
        }
        until.put(player.getUniqueId(), System.currentTimeMillis() + (long) (seconds * 1000));
    }

    /** Оставшееся время в секундах, 0 если готово. */
    public double remaining(Player player) {
        Long end = until.get(player.getUniqueId());
        if (end == null) return 0;
        long left = end - System.currentTimeMillis();
        if (left <= 0) {
            until.remove(player.getUniqueId());
            return 0;
        }
        return left / 1000.0;
    }

    /** Округление вверх до целых секунд для вывода. */
    public static String format(double seconds) {
        return String.valueOf((long) Math.ceil(seconds));
    }
}
