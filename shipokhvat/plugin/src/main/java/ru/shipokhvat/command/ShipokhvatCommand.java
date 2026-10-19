package ru.shipokhvat.command;

import org.bukkit.Bukkit;
import org.bukkit.command.Command;
import org.bukkit.command.CommandSender;
import org.bukkit.command.TabExecutor;
import org.bukkit.entity.Player;
import org.bukkit.inventory.ItemStack;
import ru.shipokhvat.ShipokhvatPlugin;
import ru.shipokhvat.util.Text;

import java.util.ArrayList;
import java.util.List;
import java.util.Locale;

public final class ShipokhvatCommand implements TabExecutor {

    private final ShipokhvatPlugin plugin;

    public ShipokhvatCommand(ShipokhvatPlugin plugin) {
        this.plugin = plugin;
    }

    @Override
    public boolean onCommand(CommandSender sender, Command command, String label, String[] args) {
        if (!sender.hasPermission("shipokhvat.admin")) {
            Text.send(sender, "no-permission");
            return true;
        }
        if (args.length == 0) {
            Text.send(sender, "usage");
            return true;
        }
        switch (args[0].toLowerCase(Locale.ROOT)) {
            case "reload" -> {
                plugin.reload();
                Text.send(sender, "reloaded");
            }
            case "give" -> give(sender, args);
            default -> Text.send(sender, "usage");
        }
        return true;
    }

    private void give(CommandSender sender, String[] args) {
        Player target;
        if (args.length >= 2) {
            target = Bukkit.getPlayerExact(args[1]);
        } else {
            target = sender instanceof Player p ? p : null;
        }
        if (target == null) {
            Text.send(sender, "player-not-found");
            return;
        }
        int amount = 1;
        if (args.length >= 3) {
            try {
                amount = Math.max(1, Math.min(64, Integer.parseInt(args[2])));
            } catch (NumberFormatException ignored) {
                Text.send(sender, "usage");
                return;
            }
        }
        for (int i = 0; i < amount; i++) {
            ItemStack item = plugin.weapon().create();
            target.getInventory().addItem(item).values()
                    .forEach(left -> target.getWorld().dropItemNaturally(target.getLocation(), left));
        }
        Text.send(sender, "given", "amount", amount, "player", target.getName());
    }

    @Override
    public List<String> onTabComplete(CommandSender sender, Command command, String alias, String[] args) {
        List<String> out = new ArrayList<>();
        if (!sender.hasPermission("shipokhvat.admin")) return out;
        if (args.length == 1) {
            for (String s : List.of("give", "reload")) if (s.startsWith(args[0].toLowerCase(Locale.ROOT))) out.add(s);
        } else if (args.length == 2 && args[0].equalsIgnoreCase("give")) {
            for (Player p : Bukkit.getOnlinePlayers()) {
                if (p.getName().toLowerCase(Locale.ROOT).startsWith(args[1].toLowerCase(Locale.ROOT))) out.add(p.getName());
            }
        }
        return out;
    }
}
