# Fair replay — 2026-09-29 — 7-day horizon

Result of record for the Buy/Hold/Sell rules. `oracle.replay` and the stats page's replay are in-sample; where they disagree with this file, this file wins.

| | |
|---|---|
| Rule version | `bea384a` (fingerprint `8defba803279`), locked 2026-09-22 |
| Cutoff | 2026-09-21: the newest price day the rules were tuned on. Only verdict dates on or after it count, so every outcome price is unseen |
| Universe | hob, msh, sos, tmt, ecl: the site's sets at lock time, frozen; rare/mythic main printings, cheapest non-foil price across all printings |
| Horizon | 7 days (**interim**: the rules were picked on 14-day returns) |
| Verdict dates | 2026-09-21 (every 7 days from the cutoff whose horizon has closed) |
| Prices through | 2026-09-28 |

## Verdicts as of 2026-09-21 → prices on 2026-09-28

388 cards scored, 0 skipped (no price on one of the two days). 5 got a new printing after 2026-09-21 (a reprint can drop the cheapest price).

| Call | n | Median | Rose | Fell | Fell 20%+ |
|---|---|---|---|---|---|
| Buy | 54 | +1.2% | 54% | 46% | 7% |
| Hold | 332 | +0.0% | 40% | 49% | 6% |
| Sell | 2 | -15.8% | 0% | 100% | 50% |
| All cards | 388 | +0.0% | 41% | 49% | 6% |

Against the cards each call could have been made on:

| Comparison | n | Median | Rose | Fell | Fell 20%+ |
|---|---|---|---|---|---|
| Buy-eligible (28+ days out, $0.50+) | 191 | -1.2% | 43% | 53% | 7% |
| Sell-eligible ($2+) | 81 | -2.2% | 38% | 59% | 10% |

- Buy: p = 0.0158, the share of random same-size picks from its pool whose median did at least as well.
- Sell: p = 0.0737, the share of random same-size picks from its pool whose median fell at least as far.

### By event window

The same price move means different things by card age: in the crash window almost everything falls, so a drop there is not a Buy signal (the rules never Buy before day 28).

| Window (age at verdict) | Call | n | Median | Rose | Fell | Fell 20%+ |
|---|---|---|---|---|---|---|
| after the crash (28+ days) | buy | 54 | +1.2% | 54% | 46% | 7% |
| after the crash (28+ days) | hold | 332 | +0.0% | 40% | 49% | 6% |
| after the crash (28+ days) | sell | 2 | -15.8% | 0% | 100% | 50% |
| after the crash (28+ days) | all | 388 | +0.0% | 41% | 49% | 6% |

**Untested on this date:** no cards were in release weeks (0-13 days) or crash window (14-27 days), so the rules for those windows (e.g. the crash-window Sell) have no fair result here.

<details><summary>Every Buy and Sell call</summary>

| Call | Card | Set | Age | Then | After | Change | New printing |
|---|---|---|---|---|---|---|---|
| buy | Thorin, Mountain-king | hob | 38d | $4.36 | $3.35 | -23% |  |
| buy | Echocasting Symposium | sos | 150d | $3.22 | $2.49 | -23% |  |
| buy | Radagast of Rhosgobel | hob | 38d | $2.49 | $1.95 | -22% |  |
| buy | Avengers Assemble! | msh | 87d | $1.86 | $1.47 | -21% |  |
| buy | Mathemagics | sos | 150d | $3.35 | $2.69 | -20% |  |
| buy | Vibrance | ecl | 241d | $2.51 | $2.06 | -18% |  |
| buy | The Last Ronin | tmt | 199d | $0.97 | $0.81 | -16% |  |
| buy | Chrome Dome | tmt | 199d | $1.11 | $0.94 | -15% |  |
| buy | Captain America, Super-Soldier | msh | 87d | $3.62 | $3.12 | -14% |  |
| buy | Triceraton Commander | tmt | 199d | $1.16 | $1.00 | -14% |  |
| buy | Kíli the Resourceful | hob | 38d | $1.19 | $1.03 | -13% |  |
| buy | Ashling, Rekindled // Ashling, Rimebound | ecl | 241d | $0.68 | $0.59 | -13% |  |
| buy | Broadcast Takeover | tmt | 199d | $0.51 | $0.46 | -10% |  |
| buy | Inside Information | hob | 38d | $1.95 | $1.78 | -9% |  |
| buy | Elrond, Moon-Reader | hob | 38d | $2.02 | $1.85 | -8% |  |
| buy | Deceit | ecl | 241d | $2.52 | $2.32 | -8% |  |
| buy | Weather Maker | tmt | 199d | $0.52 | $0.48 | -8% |  |
| buy | Leatherhead, Swamp Stalker | tmt | 199d | $1.12 | $1.05 | -6% |  |
| buy | Catharsis | ecl | 241d | $0.51 | $0.48 | -6% |  |
| buy | South Wind Avatar | tmt | 199d | $1.55 | $1.46 | -6% |  |
| buy | Planar Engineering | sos | 150d | $1.18 | $1.13 | -4% |  |
| buy | Wistfulness | ecl | 241d | $4.05 | $4.00 | -1% |  |
| buy | Quandrix, the Proof | sos | 150d | $1.42 | $1.41 | -1% |  |
| buy | Tony Stark // The Invincible Iron Man | msh | 87d | $4.16 | $4.14 | -0% |  |
| buy | Dark Leo & Shredder | tmt | 199d | $3.77 | $3.76 | -0% |  |
| buy | Ral Zarek, Guest Lecturer | sos | 150d | $1.28 | $1.29 | +1% |  |
| buy | Flashback | sos | 150d | $3.09 | $3.12 | +1% |  |
| buy | Morningtide's Light | ecl | 241d | $1.35 | $1.37 | +1% |  |
| buy | Prismari, the Inspiration | sos | 150d | $3.35 | $3.42 | +2% |  |
| buy | Loki, God of Mischief | msh | 87d | $1.27 | $1.30 | +2% |  |
| buy | My Precious // Allure of Power | hob | 38d | $1.26 | $1.29 | +2% |  |
| buy | Great Hall of the Biblioplex | sos | 150d | $0.73 | $0.75 | +3% |  |
| buy | Moseo, Vein's New Dean | sos | 150d | $0.66 | $0.68 | +3% |  |
| buy | Thranduil, the Elvenking | hob | 38d | $0.59 | $0.61 | +3% |  |
| buy | Grave Researcher // Reanimate | sos | 150d | $1.81 | $1.88 | +4% |  |
| buy | M.O.D.O.K. | msh | 87d | $4.30 | $4.48 | +4% |  |
| buy | Gandalf, Goblins' Bane // Flameshape | hob | 38d | $3.99 | $4.19 | +5% |  |
| buy | The Unbeatable Squirrel Girl | msh | 87d | $2.47 | $2.62 | +6% |  |
| buy | Emeritus of Woe // Demonic Tutor | sos | 150d | $10.81 | $11.50 | +6% |  |
| buy | Fateful Discovery | hob | 38d | $3.54 | $3.82 | +8% |  |
| buy | Champions of the Perfect | ecl | 241d | $1.24 | $1.34 | +8% |  |
| buy | Cauldron of Essence | sos | 150d | $2.46 | $2.66 | +8% |  |
| buy | The Cloning of Shredder | tmt | 199d | $0.82 | $0.90 | +10% |  |
| buy | Thanos, the Mad Titan | msh | 87d | $1.39 | $1.53 | +10% |  |
| buy | Emeritus of Truce // Swords to Plowshares | sos | 150d | $1.08 | $1.19 | +10% |  |
| buy | Withering Curse | sos | 150d | $0.91 | $1.05 | +15% |  |
| buy | Michelangelo, Improviser | tmt | 199d | $2.23 | $2.67 | +20% |  |
| buy | Earth's Mightiest Heroes | msh | 87d | $0.84 | $1.01 | +20% |  |
| buy | The Serpent Society | msh | 87d | $0.53 | $0.65 | +23% |  |
| buy | Captain America's Shield | msh | 87d | $1.17 | $1.44 | +23% |  |
| buy | Splinter, Radical Rat | tmt | 199d | $0.53 | $0.66 | +25% |  |
| buy | Celestial Reunion | ecl | 241d | $1.05 | $1.32 | +26% |  |
| buy | Rat King, Verminister | tmt | 199d | $0.74 | $0.96 | +30% |  |
| buy | Arc Reactor | msh | 87d | $0.56 | $0.93 | +66% |  |
| sell | Mutagen Man, Living Ooze | tmt | 199d | $2.83 | $2.22 | -22% |  |
| sell | Multiversal Incursion | msh | 87d | $2.30 | $2.07 | -10% |  |

</details>

## Watch (rule A)

Rule A (Jev-linked older card, links to 2+ new cards, under $3) was locked on 2026-09-22 for the next set. It has not been run on a new set yet, so it has **no fair result**. Next event: Reality Fracture (`fra`), released 2026-10-02. The list counts only if it is frozen, from pre-release prices and rules text, before the outcome window; score about 5 weeks after release.
