package ru.shipokhvat;

import org.bukkit.Material;
import org.bukkit.configuration.ConfigurationSection;
import org.bukkit.configuration.file.FileConfiguration;

import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Locale;
import java.util.Set;
import java.util.logging.Logger;

/** Снимок config.yml. Пересоздаётся при /shipokhvat reload. */
public final class Settings {

    // item
    public final Material material;
    public final String itemModel;
    public final int customModelData;
    public final double damage;
    public final double attackSpeed;
    public final boolean unbreakable;
    public final boolean glint;
    public final String name;
    public final List<String> lore;
    /** Меняется при любом изменении конфига — по нему обновляются выданные мечи. */
    public final int revision;

    // root
    public final boolean rootEnabled;
    public final double rootCooldown;
    public final double rootDuration;
    public final double rootArmTimeout;
    public final boolean rootCooldownOnActivate;
    public final boolean rootAffectMobs;
    public final boolean rootLockRotation;
    public final int rootSnapToGround;
    public final boolean rootBlockPearls;
    public final Set<String> rootBlockedTeleports;
    public final List<Material> rootStalkBlocks;
    public final int rootStalkCount;
    public final float rootStalkHeight;
    public final double rootRadius;
    public final Material rootWebBlock;
    public final float rootWebScale;
    public final Material rootGroundBlock;
    public final int rootGrowTicks;
    public final String soundRootArm, soundRootHit, soundRootHit2, soundRootRelease;

    // pull
    public final boolean pullEnabled;
    public final double pullCooldown;
    public final double pullMissCooldown;
    public final double pullRange;
    public final double pullDamageHearts;
    public final boolean pullTrueDamage;
    public final boolean pullAffectMobs;
    public final double pullVineSpeed;
    public final double pullSpeed;
    public final double pullStopDistance;
    public final int pullMaxTicks;
    public final Material pullVineBlock;
    public final float pullVineWidth;
    public final boolean pullParticles;
    public final String soundPullShoot, soundPullHit, soundPullHit2, soundPullPull, soundPullMiss;

    public final boolean actionBar;

    private final ConfigurationSection messages;

    public Settings(FileConfiguration c, Logger log) {
        material = material(c.getString("item.material"), Material.NETHERITE_SWORD, log);
        itemModel = c.getString("item.item-model", "");
        customModelData = c.getInt("item.custom-model-data", 0);
        damage = c.getDouble("item.damage", 17);
        attackSpeed = c.getDouble("item.attack-speed", 1.6);
        unbreakable = c.getBoolean("item.unbreakable", true);
        glint = c.getBoolean("item.glint", false);
        name = c.getString("item.name", "Шипохват");
        lore = c.getStringList("item.lore");

        rootEnabled = c.getBoolean("root.enabled", true);
        rootCooldown = c.getDouble("root.cooldown", 60);
        rootDuration = c.getDouble("root.duration", 3);
        rootArmTimeout = c.getDouble("root.arm-timeout", 15);
        rootCooldownOnActivate = c.getBoolean("root.cooldown-on-activate", false);
        rootAffectMobs = c.getBoolean("root.affect-mobs", true);
        rootLockRotation = c.getBoolean("root.lock-rotation", true);
        rootSnapToGround = c.getInt("root.snap-to-ground", 4);
        rootBlockPearls = c.getBoolean("root.block-ender-pearls", true);
        rootBlockedTeleports = new HashSet<>();
        for (String s : c.getStringList("root.blocked-teleport-causes")) {
            rootBlockedTeleports.add(s.toUpperCase(Locale.ROOT));
        }
        rootStalkBlocks = new ArrayList<>();
        for (String s : c.getStringList("root.visual.stalk-blocks")) {
            Material m = material(s, null, log);
            if (m != null && m.isBlock()) rootStalkBlocks.add(m);
        }
        rootStalkCount = Math.max(0, c.getInt("root.visual.stalk-count", 7));
        rootStalkHeight = (float) c.getDouble("root.visual.stalk-height", 2.1);
        rootRadius = c.getDouble("root.visual.radius", 0.55);
        rootWebBlock = material(c.getString("root.visual.web-block"), null, log);
        rootWebScale = (float) c.getDouble("root.visual.web-scale", 1.3);
        rootGroundBlock = material(c.getString("root.visual.ground-block"), null, log);
        rootGrowTicks = Math.max(1, c.getInt("root.visual.grow-ticks", 6));
        soundRootArm = c.getString("root.sounds.arm", "");
        soundRootHit = c.getString("root.sounds.hit", "");
        soundRootHit2 = c.getString("root.sounds.hit2", "");
        soundRootRelease = c.getString("root.sounds.release", "");

        pullEnabled = c.getBoolean("pull.enabled", true);
        pullCooldown = c.getDouble("pull.cooldown", 30);
        pullMissCooldown = c.getDouble("pull.miss-cooldown", 5);
        pullRange = c.getDouble("pull.range", 20);
        pullDamageHearts = c.getDouble("pull.damage-hearts", 1);
        pullTrueDamage = c.getBoolean("pull.true-damage", true);
        pullAffectMobs = c.getBoolean("pull.affect-mobs", true);
        pullVineSpeed = Math.max(0.1, c.getDouble("pull.vine-speed", 2.5));
        pullSpeed = c.getDouble("pull.pull-speed", 1.1);
        pullStopDistance = c.getDouble("pull.stop-distance", 2);
        pullMaxTicks = c.getInt("pull.max-pull-ticks", 30);
        pullVineBlock = material(c.getString("pull.visual.vine-block"), Material.MOSS_BLOCK, log);
        pullVineWidth = (float) c.getDouble("pull.visual.vine-width", 0.16);
        pullParticles = c.getBoolean("pull.visual.particles", true);
        soundPullShoot = c.getString("pull.sounds.shoot", "");
        soundPullHit = c.getString("pull.sounds.hit", "");
        soundPullHit2 = c.getString("pull.sounds.hit2", "");
        soundPullPull = c.getString("pull.sounds.pull", "");
        soundPullMiss = c.getString("pull.sounds.miss", "");

        actionBar = c.getBoolean("ui.action-bar", true);
        messages = c.getConfigurationSection("messages");
        revision = c.saveToString().hashCode();
    }

    public String message(String key) {
        return messages == null ? key : messages.getString(key, key);
    }

    private static Material material(String name, Material def, Logger log) {
        if (name == null || name.isBlank()) return def;
        Material m = Material.matchMaterial(name.trim());
        if (m == null) {
            log.warning("Неизвестный материал в конфиге: " + name);
            return def;
        }
        return m;
    }
}
