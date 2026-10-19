package ru.shipokhvat.item;

import org.bukkit.NamespacedKey;
import org.bukkit.attribute.Attribute;
import org.bukkit.attribute.AttributeModifier;
import org.bukkit.entity.Player;
import org.bukkit.inventory.EquipmentSlotGroup;
import org.bukkit.inventory.ItemFlag;
import org.bukkit.inventory.ItemStack;
import org.bukkit.inventory.PlayerInventory;
import org.bukkit.persistence.PersistentDataType;
import ru.shipokhvat.Settings;
import ru.shipokhvat.ShipokhvatPlugin;
import ru.shipokhvat.util.Text;

import java.util.ArrayList;
import java.util.List;

public final class WeaponItem {

    /** Ванильные ключи — тогда в описании пишется «17 Урон», а не «+16». */
    private static final NamespacedKey BASE_DAMAGE = NamespacedKey.minecraft("base_attack_damage");
    private static final NamespacedKey BASE_SPEED = NamespacedKey.minecraft("base_attack_speed");
    private static final double PLAYER_BASE_DAMAGE = 1.0;
    private static final double PLAYER_BASE_SPEED = 4.0;

    private final ShipokhvatPlugin plugin;
    private final NamespacedKey weaponKey;
    private final NamespacedKey revisionKey;

    public WeaponItem(ShipokhvatPlugin plugin) {
        this.plugin = plugin;
        this.weaponKey = new NamespacedKey(plugin, "weapon");
        this.revisionKey = new NamespacedKey(plugin, "revision");
    }

    public ItemStack create() {
        ItemStack item = new ItemStack(plugin.settings().material);
        apply(item);
        return item;
    }

    public boolean isWeapon(ItemStack item) {
        if (item == null || item.isEmpty() || !item.hasItemMeta()) return false;
        return item.getPersistentDataContainer().has(weaponKey, PersistentDataType.BYTE);
    }

    public boolean isHolding(Player player) {
        return isWeapon(player.getInventory().getItemInMainHand());
    }

    /** Возвращает обновлённый предмет, если конфиг менялся, иначе null. */
    public ItemStack refreshed(ItemStack item) {
        if (!isWeapon(item)) return null;
        Settings s = plugin.settings();
        Integer rev = item.getPersistentDataContainer().get(revisionKey, PersistentDataType.INTEGER);
        if (rev != null && rev == s.revision && item.getType() == s.material) return null;
        ItemStack result = item.getType() == s.material ? item.clone() : item.withType(s.material);
        apply(result);
        return result;
    }

    public void refreshInventory(Player player) {
        PlayerInventory inv = player.getInventory();
        for (int i = 0; i < inv.getSize(); i++) {
            ItemStack updated = refreshed(inv.getItem(i));
            if (updated != null) inv.setItem(i, updated);
        }
    }

    public void refreshMainHand(Player player) {
        ItemStack updated = refreshed(player.getInventory().getItemInMainHand());
        if (updated != null) player.getInventory().setItemInMainHand(updated);
    }

    @SuppressWarnings("deprecation") // setCustomModelData(int) — оставлен для старых паков
    private void apply(ItemStack item) {
        Settings s = plugin.settings();
        Object[] ph = {
                "damage", Text.num(s.damage),
                "root_duration", Text.num(s.rootDuration),
                "root_cooldown", Text.num(s.rootCooldown),
                "pull_range", Text.num(s.pullRange),
                "pull_damage", Text.num(s.pullDamageHearts),
                "pull_cooldown", Text.num(s.pullCooldown),
        };
        item.editMeta(meta -> {
            meta.displayName(Text.item(s.name, ph));
            List<net.kyori.adventure.text.Component> lore = new ArrayList<>();
            for (String line : s.lore) lore.add(Text.item(line, ph));
            meta.lore(lore);

            NamespacedKey model = s.itemModel.isBlank() ? null : NamespacedKey.fromString(s.itemModel);
            meta.setItemModel(model);
            meta.setCustomModelData(s.customModelData > 0 ? s.customModelData : null);

            meta.removeAttributeModifier(Attribute.ATTACK_DAMAGE);
            meta.removeAttributeModifier(Attribute.ATTACK_SPEED);
            meta.addAttributeModifier(Attribute.ATTACK_DAMAGE, new AttributeModifier(BASE_DAMAGE,
                    s.damage - PLAYER_BASE_DAMAGE, AttributeModifier.Operation.ADD_NUMBER, EquipmentSlotGroup.MAINHAND));
            meta.addAttributeModifier(Attribute.ATTACK_SPEED, new AttributeModifier(BASE_SPEED,
                    s.attackSpeed - PLAYER_BASE_SPEED, AttributeModifier.Operation.ADD_NUMBER, EquipmentSlotGroup.MAINHAND));

            meta.setUnbreakable(s.unbreakable);
            meta.addItemFlags(ItemFlag.HIDE_UNBREAKABLE);
            meta.setEnchantmentGlintOverride(s.glint ? Boolean.TRUE : null);
            meta.setMaxStackSize(1);

            meta.getPersistentDataContainer().set(weaponKey, PersistentDataType.BYTE, (byte) 1);
            meta.getPersistentDataContainer().set(revisionKey, PersistentDataType.INTEGER, s.revision);
        });
    }
}
