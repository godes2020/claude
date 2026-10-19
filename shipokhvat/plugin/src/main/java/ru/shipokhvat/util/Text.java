package ru.shipokhvat.util;

import net.kyori.adventure.text.Component;
import net.kyori.adventure.text.format.TextDecoration;
import net.kyori.adventure.text.minimessage.MiniMessage;
import org.bukkit.Location;
import org.bukkit.SoundCategory;
import org.bukkit.command.CommandSender;
import ru.shipokhvat.ShipokhvatPlugin;

public final class Text {

    private static final MiniMessage MM = MiniMessage.miniMessage();

    private Text() {
    }

    /** Подставляет пары {ключ} → значение и разбирает MiniMessage. */
    public static Component parse(String raw, Object... placeholders) {
        String s = raw;
        for (int i = 0; i + 1 < placeholders.length; i += 2) {
            s = s.replace("{" + placeholders[i] + "}", String.valueOf(placeholders[i + 1]));
        }
        return MM.deserialize(s);
    }

    /** Для названия и описания предмета: без курсива по умолчанию. */
    public static Component item(String raw, Object... placeholders) {
        return parse(raw, placeholders).decorationIfAbsent(TextDecoration.ITALIC, TextDecoration.State.FALSE);
    }

    public static void send(CommandSender to, String key, Object... placeholders) {
        var s = ShipokhvatPlugin.get().settings();
        String msg = s.message(key);
        if (msg.isEmpty()) return;
        to.sendMessage(parse(s.message("prefix") + msg, placeholders));
    }

    /** 3.0 → "3", 2.5 → "2.5" */
    public static String num(double v) {
        if (v == Math.rint(v)) return String.valueOf((long) v);
        return String.valueOf(Math.round(v * 10) / 10.0);
    }

    public static void sound(Location at, String key, float volume, float pitch) {
        if (key == null || key.isEmpty() || at.getWorld() == null) return;
        at.getWorld().playSound(at, key, SoundCategory.PLAYERS, volume, pitch);
    }
}
