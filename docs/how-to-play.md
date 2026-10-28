# SpaceTrader — How to Play

You are the owner of a free trader, twenty thousand credits in debt to the bank that
financed her, with a thousand credits in your account and eight tons of fuel in the tanks.
Clear the mortgage and the ship is yours. Miss two payments and it isn't.

Everything else is in service of that.

## Loading

```
LOAD ""
```

Name your ship when asked — press ENTER alone and she's the *Beowulf*.

## The screen

The top third is the world you're docked at. Below it:

```
CORIOLIS GATE          TL15 LAW 8     the system, its tech and law levels
CARGO 0 OF 20 TONS                    your hold
  GOOD        PRICE ST  HELD
1 FOODSTUFFS      23 IM     0         eight goods, priced for this port
...
6 WEAPONS        127 --     0  !      ! means contraband here
BUY SELL JUMP PORT                    press the yellow letter
CR 1000 FUEL 8 HULL 8 HEAT 0
```

`ST` is what the port does with that good: `EX` exports it and sells cheap, `IM` imports it
and pays well, `--` neither.

Press the highlighted letter to choose. Messages appear in white on black where the menu
is; press any key to clear them.

## Trading

Buy where a good is exported, sell where it's imported. That's the whole engine — an
exporter knocks 30% off, an importer adds 40%, so the spread on a full hold is real money.

Prices also shift with the world's population and tech level, and are rerolled every time
you dock, so the same route pays differently each run. Your hold is twenty tons.

The best single-jump runs pay two to three thousand credits. Ambergris to Junction Nine
with luxuries is the fattest in the sector, if you can afford the stock.

## The sector

Twenty systems on a grid. You can jump to anything **within two columns and two rows** —
so a system two squares away diagonally is still one jump. Fuel costs one ton, plus one
for every two squares of distance: one to three tons a jump.

```
        CORE  <-------------------------------------->  FRONTIER

          1   2   3   4   5   6   7   8   9  10  11  12  13
   2      .   .   3   .   9   .   .   .   .   .  20   .   .
   3      .   .   .   .   .  11   .   .  15   .   .   .  17
   4      .   1   .   .   6   .   .   .   .   .   .   .   .
   5      .   .   .  12   .   .  10   .   .  14   .   .   .
   6      2   .   5   .   .   .   .   .   .   .   .  16   .
   7      .   .   .   7   .   .   .  13  18   .   .   .   .
   8      .   4   .   .   .   8   .   .   .   .  19   .   .
```

| # | System | TL | Law | Exports | Imports |
|---:|---|---:|---:|---|---|
| 1 | Coriolis Gate | 15 | 8 | ELEC MACH | ORE FOOD |
| 2 | Meridian | 14 | 9 | MED ELEC | ORE TEXT |
| 3 | Verity | 14 | 7 | MACH ELEC | ORE FOOD TEXT |
| 4 | Tessellate | 13 | 6 | LUX | FOOD TEXT MED |
| 5 | Aldebar Prime | 13 | 6 | ELEC WEAP MACH | ORE FOOD |
| 6 | Junction Nine | 10 | 5 | MACH | FOOD LUX |
| 7 | Hollow Sky | 8 | 4 | FOOD TEXT | MACH MED |
| 8 | Kestrel | 9 | 5 | FOOD | ELEC MACH |
| 9 | Ambergris | 11 | 4 | LUX TEXT | FOOD MACH |
| 10 | Tannhauser | 11 | 5 | ELEC MACH | ORE FOOD |
| 11 | Fenwick | 8 | 3 | ORE | FOOD MED MACH |
| 12 | Pellucid | 12 | 6 | MED ELEC | FOOD TEXT LUX |
| 13 | Sable Run | 9 | 3 | TEXT | ELEC MED |
| 14 | Rust Harbour | 6 | 1 | ORE WEAP | FOOD MED ELEC |
| 15 | Cinder | 5 | 2 | ORE | FOOD MED MACH |
| 16 | Vagrant | 6 | 0 | WEAP LUX | FOOD MED MACH |
| 17 | Ossuary | 4 | 1 | ORE WEAP | FOOD MED TEXT |
| 18 | Longshot | 5 | 2 | ORE FOOD | ELEC MACH MED |
| 19 | Threadbare | 4 | 3 | FOOD TEXT | ELEC MACH MED |
| 20 | Kalideen | 7 | 2 | ORE TEXT | ELEC WEAP MED |

Everything is reachable from Coriolis Gate, but the frontier is a long way out — Ossuary
and Vagrant are six jumps, and Ossuary connects only through Kalideen. There is no way
around it: if you want the weapons at Ossuary you commit to the trip.

The gradient runs left to right. The core is high tech and high law: cheap fuel and
repairs, no pirates worth the name, and inspectors everywhere. The frontier is the
reverse — nothing legal is worth much, but nothing is illegal either, and the pirates know
it.

## Jumping

`JUMP` lists everything in reach, with `F` showing the fuel cost. Pick a number, or `C` to
stay put. A jump is committed the moment you choose it — the encounter roll happens in
transit, and you arrive with whatever you have left.

You can't refuel in deep space. Watch the tanks: at three tons a jump, eight tons is not
as far as it sounds.

## Contraband

Four goods are restricted, and the higher a world's law level, the more it cares:

| Good | Restricted above law | Illegal in | License |
|---|---:|---:|---:|
| Weapons | 4 | 9 of 20 | 1440 |
| Luxuries | 5 | 6 of 20 | 2000 |
| Electronics | 6 | 3 of 20 | 1120 |
| Medical | 7 | 2 of 20 | 720 |

A `!` on the market screen means that good is contraband *here*. Buying it raises your
heat. Carrying it is what customs are looking for.

Buy a **license** at any port and that good stops being contraband for you anywhere. It's
expensive, and it's the alternative to running hot.

## Heat

Heat is how much attention you've attracted. It rises when you buy contraband (+2), and
much faster when an inspection goes badly — complying costs 4, a failed bribe 8, resisting
15. It falls by one with every jump.

Heat makes everything worse at once. Customs inspect you more often, pirates find you more
often, and bribes get more expensive. There's no way to pay it off; you just have to run
clean for a while.

## Customs

You're inspected on arrival, and sometimes stopped in transit by a patrol. The odds depend
on the world's law level — 10% out on the frontier, 25% in the middle band, 45% in the
core — plus a fifth of your heat, capped at 70%. Transit stops are half as likely.

If the hold is clean, nothing happens. If it isn't:

| | What it costs |
|---|---|
| **Comply** | Pay 40 credits a ton, lose the cargo, heat +4 |
| **Bribe** | 70% less your heat, minimum 20%. Works: nothing happens. Fails: double fine, cargo gone, heat +8 |
| **Surrender** | Lose the cargo, heat +1. No fine |
| **Resist** | Fight a patrol cutter, which is tougher than a pirate, and take heat +15 either way |

Surrendering is usually right when you're caught cold. Bribing is a gamble that gets worse
the hotter you are — which is exactly when you most want it to work.

## Pirates and patrols

Rolled on every jump against the destination's law level:

| Destination | Pirate | Patrol | Trade offer |
|---|---:|---:|---:|
| Frontier (law 0–2) | 25% | 2% | 15% |
| Middle (law 3–5) | 12% | 8% | 15% |
| Core (law 6+) | 3% | 20% | 12% |

Heat adds to both the pirate and patrol chances. The frontier is where the money is and
where the pirates are; the core is safe from pirates and thick with inspectors.

In a fight:

| | |
|---|---|
| **Evade** / **Run** | 50% plus 3 per ton of fuel. Fail and you lose hull and cargo |
| **Fight** | Your hull against theirs, both plus a die roll. Win and they break off. Lose and you take 1–2 hull and lose cargo |
| **Bribe** | 200 credits, 60% less your heat, minimum 15% |

Nobody kills you outright. You lose cargo and hull — but hull reaching zero ends the run.

## Port services

`PORT` from the market screen:

- **Fuel** — one ton, or fill the tanks. Costs less at high tech worlds: 10 credits a ton
  at TL15, 32 at TL4.
- **Hull** — one point, 40 to 84 credits depending on tech level.
- **Licenses** — see above.
- **Mortgage** — pays 1000 off the principal.

High-tech core worlds are the cheap place to repair and refuel. They're also where
contraband is most dangerous.

## The mortgage

Twenty thousand credits. Every eight jumps, 800 falls due and is taken automatically if
you have it.

Miss one and you get a warning. **Miss two and the ship is repossessed.**

Paying the minimum takes forever — 200 jumps. Paying down the principal at port after a
good run clears it in a handful. That's the game: the minimum keeps you alive, the profits
buy you out.

## How you lose

- **Hull to zero** in a fight
- **Two missed payments**
- **Stranded** — no fuel, no cargo to sell, and not enough credits to buy a ton

That last one is the quiet one. Don't spend your last credits on cargo you can't move.

## How you win

Clear the debt. She's yours.

## A first run

Coriolis Gate exports electronics and machinery and imports ore and foodstuffs. It's a
core world — law 8, so weapons, luxuries, electronics and medical are all contraband
there, and inspections are frequent.

Buy electronics, jump toward the middle band, sell into a world that imports them. Come
back with ore. Once you've a few thousand in hand, decide whether to buy a weapons license
and run the frontier routes, or stay legal and grind the core runs.

The frontier pays better. It's also where the pirates are, and where your heat will already
be high by the time you get there.
