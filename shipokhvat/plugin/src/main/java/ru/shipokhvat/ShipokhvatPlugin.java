package ru.shipokhvat;

import org.bukkit.entity.Player;
import org.bukkit.plugin.java.JavaPlugin;
import ru.shipokhvat.ability.Cooldowns;
import ru.shipokhvat.ability.PullAbility;
import ru.shipokhvat.ability.RootAbility;
import ru.shipokhvat.command.ShipokhvatCommand;
import ru.shipokhvat.item.WeaponItem;
import ru.shipokhvat.listener.WeaponListener;
import ru.shipokhvat.util.Text;

public final class ShipokhvatPlugin extends JavaPlugin {

    private static ShipokhvatPlugin instance;

    private Settings settings;
    private WeaponItem weapon;
    private RootAbility root;
    private PullAbility pull;

    public static ShipokhvatPlugin get() {
        return instance;
    }

    @Override
    public void onEnable() {
        instance = this;
        saveDefaultConfig();
        settings = new Settings(getConfig(), getLogger());

        weapon = new WeaponItem(this);
        root = new RootAbility(this);
        pull = new PullAbility(this);

        getServer().getPluginManager().registerEvents(new WeaponListener(this), this);
        ShipokhvatCommand cmd = new ShipokhvatCommand(this);
        var command = getCommand("shipokhvat");
        if (command != null) {
            command.setExecutor(cmd);
            command.setTabCompleter(cmd);
        }

        getServer().getScheduler().runTaskTimer(this, root::tick, 1L, 1L);
        getServer().getScheduler().runTaskTimer(this, this::uiTick, 10L, 10L);
    }

    @Override
    public void onDisable() {
        if (root != null) root.releaseAll();
        if (pull != null) pull.cancelAll();
    }

    public void reload() {
        reloadConfig();
        settings = new Settings(getConfig(), getLogger());
        for (Player p : getServer().getOnlinePlayers()) weapon.refreshInventory(p);
    }

    /** Раз в полсекунды: обновление мечей в руке и КД над хотбаром. */
    private void uiTick() {
        for (Player p : getServer().getOnlinePlayers()) {
            if (!weapon.isHolding(p)) continue;
            weapon.refreshMainHand(p);
            if (!settings.actionBar) continue;
            String rootState = root.isArmed(p) ? settings.message("actionbar-armed") : state(root.cooldowns().remaining(p));
            String pullState = state(pull.cooldowns().remaining(p));
            p.sendActionBar(Text.parse(settings.message("actionbar"), "root", rootState, "pull", pullState));
        }
    }

    private String state(double left) {
        return left > 0 ? settings.message("actionbar-cooldown").replace("{time}", Cooldowns.format(left))
                : settings.message("actionbar-ready");
    }

    public Settings settings() {
        return settings;
    }

    public WeaponItem weapon() {
        return weapon;
    }

    public RootAbility root() {
        return root;
    }

    public PullAbility pull() {
        return pull;
    }
}
