# High-energy theory modules

These are **method-selection notes**, not executable physics solvers, exhaustive textbooks or certifications. Load only the module whose objects and attack surface match the question. The CLI currently executes generic declared Python programs; it has no domain-specialized solvers.

> 中文摘要：按研究对象按需取用以下模块；每个模块给出适用条件、最小输入、承重检查和 kill test，但不代表系统已实现相应求解器。

Each module below gives use conditions, minimum inputs, methods, load-bearing checks, and kill tests.

## Domain procedures: trigger, inputs, checks, kill tests

### QFT, EFT, and RG

**Use when:** the target is a correlator, perturbative observable, operator mixing, matching, running coupling, or EFT regime. **Minimum inputs:** action/field content, dimension and signature, state/boundary data, symmetries/gauge fixing, observable and normalization, perturbative order/power counting, regulator/scheme and scale. **Method:** derive rules/order from the action; power-count retained and omitted operators; show loop integrals, regulator and counterterms; match the same observable at a common scale/scheme; derive the beta-function convention. **Load-bearing checks:** dimensions, protected/Ward identities, known limits, threshold consistency, and whether expansion/flow remains controlled. **Kill tests:** wrong dimensions/symmetry; protected-identity failure; decoupling mismatch; scheme change presented as universal while counterterms are fixed; expansion parameter outside its claimed range. These falsify the affected result, not QFT as a whole.

### Gauge theory and amplitudes

**Use when:** studying an on-shell amplitude, gauge relation, soft/collinear behavior, factorization, or unitarity. **Minimum inputs:** gauge group/representations, particle masses/spins/helicities, action and coupling conventions, external states/momentum conventions, kinematic domain, perturbative order, IR treatment and observable normalization. **Method:** reduce structures by symmetry/helicity; calculate at fixed convention; distinguish regulated amplitudes from inclusive/factorized observables. **Load-bearing checks:** physical gauge/polarization independence, dimensions and crossing where applicable, factorization residues, soft limits, unitarity cuts against the stated intermediate states and order. **Kill tests:** physical result depends on a pure-gauge polarization shift; residue fails factorization; cut has wrong states/order; IR-divergent expression is called finite without prescription; crossing is used outside its domain.

### CFT, BCFT, and DCFT

**Use when:** conformal data, OPE/crossing, boundary or defect/interface observables, or boundary states matter. **Minimum inputs:** dimensions, geometry, preserved symmetry, bulk/boundary/defect operator data and normalization, state and boundary/interface conditions, observable/channel, contact-term conventions, regulator and limits. **Method:** classify symmetry-allowed structures; decompose the same correlator in relevant OPE/boundary/defect channels; derive boundary/interface conditions from the declared variational problem; state hypotheses of channel/modular relations. **Load-bearing checks:** scaling/covariance, selection rules, compatible channel constraints, and admissible class of boundary data. **Kill tests:** forbidden structure under preserved symmetry; inconsistent channel data for the same object; missing boundary/defect term or degrees of freedom; contact-term or limit ambiguity concealed as a universal coefficient. One solvable representative is not a classification.

### Gravity and holography

**Use when:** field equations, horizons, asymptotic charges, black-hole response, gravitational entropy, or a bulk-boundary dictionary are at issue. **Minimum inputs:** dimension/signature, full action including boundary/joint terms, geometry/topology, matter, state/ensemble, boundary or cutoff data, observable/reference subtraction, regulator/order of limits, approximation/backreaction order. **Method:** vary the full action and display boundary terms; derive constraints/junction data; calculate observables from fixed definitions; for holography identify boundary data/dictionary and match the same state and observable on both sides. **Load-bearing checks:** permitted variations, orientations/signs, constraints, reference limit, counterterms, approximation domain and limit order. **Kill tests:** uncanceled boundary variation; incompatible constraints; failed declared limit; residual cutoff/subtraction dependence presented as invariant; bulk/boundary observable mismatch. A solution or entropy formula alone does not prove factorization, unitarity, or emergence.

### Quantum information

**Use when:** entropy, distinguishability, channels, recovery, quantum codes, or information flow is the target. **Minimum inputs:** state/ensemble, subsystem algebra or factorization, channel and reference system, continuum regulator/boundary data, information measure/normalization, observable, approximation order. **Method:** derive from the specified density matrices/channel or algebraic definition; keep comparisons on the same algebra, state and regulator; if using gravity, check information and gravitational prescription separately. **Load-bearing checks:** positivity, normalization/trace preservation, pure/product limits, and hypotheses of data-processing or entropy inequalities. **Kill tests:** invalid state/channel; required positivity/monotonicity fails; different algebras are compared as one subsystem; regulator-dependent divergence is called universal. A complexity proxy is not itself evidence of physical information recovery.

### Strings and supersymmetry

**Use when:** worldsheet consistency, branes/duality, supersymmetric spectra, or protected quantities are load-bearing. **Minimum inputs:** worldsheet/spacetime action, target-space dimension/background/fluxes, sectors and brane boundary conditions, coupling/expansion regime, preserved supercharges, moduli, observable and normalization, anomaly/tadpole assumptions. **Method:** check degrees of freedom and consistency conditions; derive preserved supersymmetry from variations with the stated boundary data; for indices/non-renormalization state protection hypotheses and allowed deformations; for dualities map charges, moduli, couplings and observables. **Load-bearing checks:** anomaly/tadpole cancellation, symmetry variations, sector completeness, low-energy and perturbative limits, nonperturbative/global corrections. **Kill tests:** violated consistency condition; incompatible charge/sector map; claimed supercharge fails on background/boundary; index used without the needed gap/compactness/protection assumption; regime extrapolation without control. Protected-sector agreement is not full-theory equivalence.

## Select the smallest decisive test

Before transferring a module, check that target and method share the object, observable, and admissible assumptions. Name the omitted datum that could change the inference, choose the cheapest relevant check, and state whether a failed test is a physical counterexample or a method mismatch. If needed assumptions or domain cannot be supplied, narrow or reframe the claim; do not convert a module mismatch into a universal no-go. These are method guides only: no domain-specific solver is implemented by v0.1.
