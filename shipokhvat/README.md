# Шипохват — плагин для Paper 1.21.11

Легендарное оружие (без крафта, выдаётся командой/на ивенте). Урон 17.

## Способности
| Кнопка | Способность | По умолчанию |
|---|---|---|
| **ПКМ** | *Хватка лозы* — следующий удар опутывает цель лозой: нельзя ходить, прыгать, поворачивать камеру, бросать эндер-жемчуг и есть хорус. После окончания цель свободна. | 3 сек, КД 60 сек |
| **Shift + ПКМ** | *Притягивание* — лоза летит до 20 блоков, наносит 1❤ сквозь броню, Защиту и Сопротивление и притягивает цель к владельцу. | КД 30 сек (5 сек при промахе) |

Над хотбаром, пока меч в руке, показывается КД обеих способностей.
Если PvP выключен / цель в защищённом регионе (WorldGuard и т.п.) — способности её не трогают.

## Команды
- `/shipokhvat give [игрок] [кол-во]` (алиас `/shk`) — выдать меч
- `/shipokhvat reload` — перечитать конфиг

Права: `shipokhvat.admin` (op), `shipokhvat.bypasscooldown` — без КД.

## Настройки
Всё в `plugins/Shipokhvat/config.yml`: урон, скорость атаки, КД, длительность, дальность,
урон притягивания, скорость лозы, визуал, звуки, все сообщения (MiniMessage).
После `/shipokhvat reload` уже выданные мечи обновляются сами.

## Сборка
```
cd plugin && mvn package      # → plugin/target/Shipokhvat-1.0.0.jar
cd resourcepack && ./build.sh # → Shipokhvat-ResourcePack.zip + SHA-1
```

## Ресурс-пак
Меч использует компонент `item_model = shipokhvat:shipokhvat` (1.21.4+), поэтому ванильные
незеритовые мечи не меняются.

```
resourcepack/
  pack.mcmeta                                   (формат 75 = 1.21.11)
  assets/shipokhvat/items/shipokhvat.json       — определение предмета
  assets/shipokhvat/models/item/shipokhvat.json — МОДЕЛЬ (сейчас заглушка)
  assets/shipokhvat/textures/item/shipokhvat.png — текстура (сейчас заглушка)
```
Чтобы поставить свою модель из Blockbench: экспорт *Java Block/Item* →
заменить `models/item/shipokhvat.json`, текстуры положить в `textures/item/`
и в модели указать их как `"shipokhvat:item/<имя>"`.

Раздача всем игрокам — в `server.properties`:
```
resource-pack=<прямая ссылка на zip>
resource-pack-sha1=<sha1 из build.sh>
require-resource-pack=true
```
