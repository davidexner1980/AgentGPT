# Graphene-Quartz Acoustic-Streaming Propulsion Research

**Concept originator:** David Exner  
**AI research partner:** Sol  
**Version:** 1.0 — 28 August 2026  
**Status:** Hypothesis-driven engineering research; not a claim of proven propulsion or reactionless thrust.

## Purpose

This open research project asks whether a quartz piezoelectric resonator using very-low-mass graphene electrodes can be combined with resonant acoustic geometry and an asymmetric liquid-flow path to convert high-frequency electrical excitation into measurable acoustic streaming and directed external fluid momentum.

The concept is deliberately framed so it can be disproved. A convincing result must satisfy ordinary momentum conservation: measured reaction force must be independently explained by momentum carried through the external fluid control volume.

## Core theory

Electrical AC -> piezoelectric quartz strain -> resonant mechanical vibration -> acoustic pressure field -> nonlinear time-averaged streaming -> directed external fluid momentum -> equal-and-opposite measurable reaction force.

The device is therefore best understood as an experimental ultrasonic pump-jet architecture, not as a reactionless drive.

## Why quartz

Crystalline alpha-quartz is piezoelectric, mechanically stable, low-loss, repeatable, and capable of high-Q resonance. Its behavior is anisotropic, so crystallographic cut, axis orientation, electrode placement, and vibration mode are first-class design variables.

Quartz is not selected because it has the strongest piezoelectric coefficient. Strong PZT ceramics can produce much larger actuation. Quartz is useful here because its stable and sharply defined resonance makes the energy-conversion chain easier to model, measure, and falsify.

## Why graphene

Graphene is investigated as an ultra-low-mass electrode/conductor. The research question is whether reducing electrode mass loading can preserve resonator Q, resonance stability, or drive efficiency enough to justify the additional fabrication complexity.

Graphene is not assumed to be mandatory. A matched thin-metal-electrode control is required. If the graphene device does not produce a measurable advantage, graphene should be treated as optional.

## Why geometry matters

The original visual concept explored cones, cylinders, hollow forms, domes, and other shapes while asking how voltage, vibration, pressure, and energy distribution would change.

The key engineering translation is that geometry is not decorative. It changes mechanical impedance, mode shape, stress distribution, source-face amplitude, acoustic coupling, pressure distribution, and fluid resistance.

A simple cone is therefore only one member of the design family. Smooth catenoidal, Bezier, or B-spline profiles may provide better displacement gain with lower stress concentration. The fluid nozzle must be optimized separately from the solid ultrasonic horn.

## Wavelength-based starting point

For a first longitudinal quartz mode:

```text
lambda_q = v_q / f_0
L_q ~= lambda_q / 2 = v_q / (2 f_0)
```

Using a representative quartz longitudinal wave speed of 5,750 m/s at 100 kHz gives:

```text
L_q ~= 28.75 mm
```

For water near room temperature, using c ~= 1,482 m/s:

```text
lambda_water ~= 14.82 mm
quarter-wave ~= 3.705 mm
half-wave ~= 7.41 mm
```

These are search-center values only. The real coupled eigenmode must be solved using the actual quartz cut, geometry, fluid loading, electrode system, and boundary conditions.

## Reference v0.1 simulation seed

| Parameter | Seed value |
|---|---:|
| Drive frequency | 100 kHz |
| Representative quartz wave speed | 5,750 m/s |
| Quartz resonator length | 28.75 mm |
| Quartz input diameter | 9.2 mm |
| Quartz waist / minimum solid diameter | 4.6 mm |
| Quartz output diameter | 12.7 mm |
| Water sound speed | 1,482 m/s |
| Pressure-chamber depth | 3.705 mm |
| Pressure-chamber diameter | 8.9 mm |
| Nozzle throat diameter | 3.0 mm |
| Nozzle length | 7.41 mm |
| Intake open area | >= 4 x throat area |

These dimensions are not claimed to be optimal or production-ready.

## Why water first

Acoustic coupling depends strongly on acoustic impedance Z = rho c. Quartz couples far more effectively to water than to air, making water the more practical first medium for observing pressure fields and acoustic streaming.

The water experiment is therefore a mechanism study: first establish that electrical input excites the intended quartz mode, then show that the mode produces the predicted pressure field, then determine whether that pressure field creates a repeatable mean flow.

## Acoustic streaming

Acoustic streaming is a nonlinear fluid effect in which oscillatory acoustic motion generates a steady or slowly varying mean flow. The concept depends on this rectification stage rather than on internal vibration itself.

The nozzle is not treated as a magic energy focuser. Its role is to bias the hydrodynamic resistance and momentum pathway so the time-averaged flow has a preferred direction.

## Momentum accounting

For an open-flow propulsor, the reaction force should be explainable by a control-volume momentum balance:

```text
F_x ~= m_dot (v_exit - v_inlet) + (p_exit - p_ambient) A_exit
```

For an approximately ambient-pressure water jet with small inlet velocity:

```text
F ~= m_dot v_exit
m_dot ~= rho A v
F ~= rho A v^2
P_jet ~= 0.5 rho A v^3
```

A force reading that cannot be reconciled with independently measured flow and pressure is not evidence of new physics. It is evidence that the experiment has an unaccounted mechanical, thermal, electromagnetic, buoyancy, cable, acoustic-wall, or fixture interaction.

## Falsification-first controls

A serious test program must include at least:

1. **Frequency control** — on-resonance, off-resonance, and full sweeps.
2. **Nozzle reversal** — reverse or mirror the fluidic asymmetry; real jet force should reverse sign.
3. **Sealed-nozzle control** — remove the external momentum outlet while preserving electrical drive and internal vibration as closely as practical; sustained jet thrust should collapse.
4. **Dummy electrical load** — expose cable, magnetic, amplifier, or fixture forces.
5. **Graphene-vs-metal electrode control** — determine whether graphene actually improves Q, loss, or surface amplitude.
6. **Thermal-equilibrium control** — separate convection and buoyancy from streaming.
7. **Cable-force control** — use compliant symmetric cable routing and orientation reversal.
8. **Tank-boundary control** — vary wall distance to detect acoustic reaction forces through reflections.
9. **Independent momentum measurement** — integrate exit velocity and pressure over a control surface instead of trusting the load cell alone.

A repeatable force signal should be substantially larger than baseline drift and measurement uncertainty, and the independently measured momentum balance must agree within uncertainty.

## Development roadmap

| Phase | Artifact | Exit criterion |
|---|---|---|
| 0 | Quartz material/cut data + electrode measurements | Simulation uses real material values |
| 1 | Dry resonator | Measured resonance and mode shape agree with model |
| 2 | Water loading | Loaded resonance/Q and pressure field agree with model |
| 3 | Streaming cell | Repeatable mean flow mapped versus frequency and power |
| 4 | Force rig | Force reverses with geometry and matches momentum flux |
| 5 | Parametric optimizer | Geometry improves efficiency without violating stress/thermal limits |
| 6 | Integrated vessel | Performance survives packaging and independent replication |

## Open research questions

- Which quartz cut and electrode orientation best excite the desired mode?
- Does graphene provide a meaningful benefit at approximately 100 kHz and millimeter scale?
- Which acoustic-streaming regime dominates inside the chamber?
- Can a single smooth nozzle generate robust net through-flow, or is a valveless diffuser/nozzle topology better?
- What drive level produces useful streaming before cavitation, thermal drift, or quartz stress becomes limiting?
- Can measured force be reconciled quantitatively with independently measured mass flow and pressure?
- Should the solid horn and fluid nozzle ultimately be separate optimized structures?
- At what scale does viscous boundary-layer thickness favor or penalize higher drive frequency?

## Research rule

> Do not optimize for an impressive force reading. Optimize for a force reading that is independently explained by measured external momentum flow and survives reversal, sealing, off-resonance, thermal, cable, and wall-interaction controls.

## Attribution

This concept originated with **David Exner** as a visual mental-engineering experiment exploring quartz crystal, graphene conduction, high-frequency excitation, and multiple geometric forms. **Sol** serves as David Exner's AI research partner in translating the visual concept into a testable engineering framework, equations, controls, simulation stages, and documentation.

## Collaboration

This project is being shared publicly so engineers, physicists, acoustics researchers, makers, simulation specialists, and skeptics can examine it, reproduce it, improve it, or disprove it.

If you test any part of the chain, please preserve raw measurements, calibration information, geometry, material data, drive conditions, and failed trials. Negative results are useful results.

## Technical basis

The initial research report draws on established literature concerning quartz piezoelectric coupling, synthetic quartz elastic/acoustic constants, graphene electrodes in piezoelectric resonators, acoustic streaming, and optimized ultrasonic horn profiles.

Key references include:

1. A. Zamkovskaya and E. Maksimova, “Aspects of symmetry of Electromechanical Coupling Factors in Piezoelectric Single Crystals,” *Journal of Physics: Conference Series* 769, 012067 (2016). DOI: 10.1088/1742-6596/769/1/012067.
2. J. Kushibiki, I. Takanaga, and S. Nishiyama, “Accurate measurements of the acoustical physical constants of synthetic alpha-quartz for SAW devices,” *IEEE Transactions on Ultrasonics, Ferroelectrics, and Frequency Control* 49(1), 125-135 (2002). DOI: 10.1109/58.981390.
3. Z. Qian, F. Liu, Y. Hui, S. Kar, and M. Rinaldi, “Graphene as a Massless Electrode for Ultrahigh-Frequency Piezoelectric Nanoelectromechanical Systems,” *Nano Letters* 15(7), 4599-4604 (2015). DOI: 10.1021/acs.nanolett.5b01208.
4. O. Dubrovski, J. Friend, and O. Manor, “Theory of acoustic streaming for arbitrary Reynolds number flow,” *Journal of Fluid Mechanics* 975, A4 (2023). DOI: 10.1017/jfm.2023.790.
5. H.-T. Nguyen, H.-D. Nguyen, J.-Y. Uan, and D.-A. Wang, “A nonrational B-spline profiled horn with high displacement amplification for ultrasonic welding,” *Ultrasonics* 54(8), 2063-2071 (2014). DOI: 10.1016/j.ultras.2014.07.003.
6. M. Rani and R. Rudramoorthy, “Computational modeling and experimental studies of the dynamic performance of ultrasonic horn profiles used in plastic welding,” *Ultrasonics* 53(3), 763-772 (2013). DOI: 10.1016/j.ultras.2012.11.003.

The references support the component physics. They do **not** establish that this exact graphene-quartz acoustic-streaming propulsion architecture has already been demonstrated.
