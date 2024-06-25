# Robust Benchmarking Strategy for Organic Thin-Film Transistors
[![NPM](https://img.shields.io/npm/l/react)](https://github.com/RodrigoSantosB/speech-recognition-signal-project/blob/main/LICENSE) 

# About The Project 
Organic thin-film transistors (OTFTs) use organic semiconductors to generate electronic responses. Operating with three terminals, these devices control the flow of current between the source and drain electrodes by applying voltage to a gate electrode. OTFT technology is assessed through reports on important parameters such as threshold voltage, carrier mobility, and series resistance. However, conventional parameter extraction methods tailored for silicon transistors may yield inaccurate results for OTFTs.

The application aims to determine the intrinsic parameters of the transistor using experimental data of current and voltage. This approach makes it possible to evaluate the quality of curve fitting using metrics such as mean squared error and relative error. Such analysis is particularly significant in establishing an intra- and inter-technology reference standard, employed as a substrate. Furthermore, our application is designed to be user-friendly as it has been developed in Python, additionally capable of execution in a cloud environment (Google Colaboratory).

## **Objective**
The optimization of parameters for TFT devices is a crucial process in the manufacture of thin-film electronics. The primary reason for performing this optimization is to enhance the performance of the devices, making them more efficient, reliable, and cost-effective. The goal is to optimize specific parameters within a model that will provide the best results for the production of these devices. A simplified way to describe how the model operates can be given by the relationship $I_D = F(V_{GS}, V_{DS})$, where:

- **$I_D$**: Electric current flowing between the source and drain terminals of a thin-film transistor (TFT).
- **$V_{GS}$**: Voltage applied to the gate terminal of the transistor, controlling the current flowing between the source and drain terminals.
- **$V_{DS}$**: Voltage applied to the drain terminal of the transistor, determining the current flowing between the source and drain terminals when the gate voltage is held constant.

The voltages $V_{GS}$ and $V_{DS}$ are fundamental for the operation of the TFT and for the optimization of its parameters, which can be obtained from the device's transfer and output curves. From these operations, it is possible to derive information about its parameters such as $V_{tho}$, $l$, $n$, $J_D$, $\delta$, $R_S$, $\lambda$, and $V_{crit}$. The model, by constraining these parameters, allows for the simultaneous adjustment of all values.

Parameter optimization is performed using a nonlinear least squares solver, which enables efficient and unambiguous adjustment of the parameters. This approach provides a better understanding of the TFT's behavior and optimizes its operation for specific applications. Moreover, parameter optimization is essential to ensure the quality and reliability of the device, as well as its integration into complex electronic circuits.

## **Conceptual schema**
![CONCEPT_MODEL](https://github.com/RodrigoSantosB/speech-recognition/blob/main/images/concept_model.png)

## **Model Description**
TFTs are electronic switches where the current flows from the source to the drain terminal, controlled by the voltage applied to the gate terminal, as shown in Fig. 1. Reference models must consistently reproduce the current-voltage characteristics of TFTs with a minimal number of parameters. This means that the model parameters can be reliably and unambiguously extracted from experimental curves.

The simplest physical representation of the drain current in a TFT involves mobile charges modulated by the gate-source voltage, $V_{GS}$, moving at a speed influenced by the drain-source voltage, $V_{DS}$. For very high source-drain electric fields, the carrier velocity saturates. As the carriers move from the source to the drain, they encounter a potential barrier, which acts as a bottleneck for charge transport. The limited rate of charge injection at the top of this potential barrier can be described as a virtual source (VS).

<p align="center">
<img src="https://github.com/RodrigoSantosB/Model_OTFT/blob/master/figures/semicondutor.png" alt="Fig 1 Seções transversais esquemáticas de (a) um coplanar e (b) um OTFT escalonado. As linhas tracejadas mostram os caminhos atuais esperados." height="300" width="800">
</p>

The mathematical model to which the experimental data will be subjected consists of a set of equations, where each variable has its degree of importance and contribution. Below is the prototype of this model, along with the description of each parameter:

The drain current of a TFT consists of mobile charges $Q_{free}$ modulated by the gate voltage, which move with a speed modulated by the drain voltage. In high source-to-drain electric fields, the velocity of the charge carriers saturates at a value $V_{sat}$. However, the charge carriers need to overcome a potential barrier on their path from the source to the drain, representing a bottleneck for charge carrier transport. The limited rate of charge injection at the top of the potential barrier can be described as a virtual source (VS). The modified $V_{sed}$ model suggests a specific form of the drain current per gate width $W$ at the VS:

$$J_D = \frac{I_D}{W} = V_{sat}.F_{sat}.Q_{free} $$

where:

- $J_D$ is the drain current density per unit width,
- $I_D$ is the drain current,
- $W$ is the gate width,
- $V_{sat}$ is the saturation velocity of the charge carriers,
- $F_{sat}$ is the saturation factor,
- $Q_{free}$ are the free mobile charges modulated by the gate voltage.

This model highlights the importance of the saturation velocity of charge carriers and the potential barrier as critical factors in the performance of TFTs.

Some charged particles are not mobile. In certain cases, an exponential tail of trap states, extending from the valence band edge into the band gap, can relate the free and total charge carrier densities through a power law. This occurs because all states are occupied according to the same quasi-Fermi level, as shown in Equation (B4) in [8] and its preceding derivation. Thus, the equation is expressed as:

$$Q_{free} = q.σ_v.\biggl(\frac{Q_{tot}}{q.σ_{traps}}\biggr)^l$$

where:

- $Q_{free}$ is the free charge carrier density,
- $Q_{tot}$ is the total charge carrier density,
- $q$ is the elementary charge,
- $\sigma_v$ is a proportionality factor related to the free states,
- $\sigma_{traps}$ is a proportionality factor related to the trap states,
- $l$ is a characteristic exponent that describes the relationship between the free and trapped states.

This equation illustrates the dependence of the free charge carrier density on the total charge carrier density, modulated by the proportionality factors $\sigma_v$ and $\sigma_{traps}$, and the exponent $l$, reflecting the distribution of trap states in the material.

In this context, $\sigma_v$ and $\sigma_{traps}$ represent the density of valence states and trap states in a single layer of the semiconductor at the virtual source (VS), respectively. The value of the exponent $l$ is determined by the ratio of the effective "temperature" that defines the exponential energy distribution of the trap states and the device temperature, originating from the Boltzmann energy distribution of the free charge carriers. However, since the exact distribution of traps is generally unknown, $l$ is treated as a model parameter. The distinction between free and trapped charge carriers, as presented in Equation (2), is the primary adaptation of the VSED framework for thin-film materials proposed in this work.

For a depleted semiconductor, an exponential accumulation of holes (positive charges) is expected with the increase of the gate field, which ceases when substantial shielding by the accumulated charge sheet is established. The following phenomenological expression, first proposed in [9], is employed:

$$Q_{tot} = C_I.n.V_T.ln \biggr[ 1 + e^{ψ.V_S − V_{GS}} . n . V_T \biggr],$$
$$ψ.V_S = V_{tho} + |δ|.V_{DS}$$

The gate insulator capacitance depends on the dielectric constant $\varepsilon$ and the insulator thickness $t_I$: $C_I = \frac{\varepsilon}{t_I}$. The thermal voltage is represented by $V_T = \frac{kT}{q}$. The transition from weak to strong accumulation is modeled by the parameters $n$, $V_{th0}$, and $\delta$, where the parameter $n$ is influenced by the charging of the semiconductor region adjacent to the gate insulator interface, filling surface states and affecting the band bending rate with gate biasing.

The interface potential becomes independent of $V_{GS}$ when it reaches a bias value $\psi \cdot V_S$, also known as the threshold voltage. This allows for parameterizing the potential barrier control by gate bias in TFTs. The parameter $\psi \cdot V_S$ represents the critical bias at which the potential at $V_S$ becomes independent of the gate voltage. During the accumulation of holes at the gate insulator interface, the parameters $n$ and $l$ describe the charging of trap states, and the voltage scale for the exponential increase of the drain current with gate bias is given by $\left( \frac{n}{l} \right) \cdot V_T$ in the VSED model. The parameter $\delta$ does not necessarily represent DIBL (drain-induced barrier lowering).

The injection velocity of charges $Q_{free}$ into the transistor channel is represented by $V_{inj} = V_{sat} \cdot F_{sat}$. It is common to estimate the drain current in TFTs as a drift motion of the injected charge carriers, but this can lead to a mistaken conclusion about the saturation velocity $V_{sat}$. While in high electric field regions the saturation velocity equals the saturation velocity in the bulk semiconductor, in low electric field regions the saturation velocity is defined by the unidirectional thermal velocity of the quasi-Fermi potential and not the electrostatic potential. This concept is discussed in [10]:
$$V_{sat}=\frac{2D}{\bar{λ}_{free}}=\frac{2.μ.V_T}{\bar{λ}\_{free}}$$ 

which is parameterized here by the diffusion coefficient $D$ and can be related to the drift mobility $\mu$ through the Einstein relation. At low drain bias, charge carrier diffusion is the dominant transport mechanism in much of the TFT, not just at the virtual source $V_S$. The characteristic length in Eq. (5) will no longer be given by the mean free path $\bar{\lambda}_{free}$ but by the diffusion length. Since only one type of charge carrier is injected into an essentially intrinsic semiconductor, the diffusion length can be very large and comparable to the device dimension given by the gate length $L_G$. $F_{sat}$ introduces a length scale $\lambda = \frac{L_G}{\bar{\lambda}_{free}}$, which effectively replaces $\bar{\lambda}_{free}$ with $L_G$ at low drain bias.

The remaining function $F_{sat}$ describes the depletion of the accumulated holes. For long-channel TFTs, the diffusion and emission theory [11, 5] represents an interesting approach to determine $F_{sat}$:

$$F_{sat} = \frac{1}{1 + 2t}.\frac{1-e^{\Bigl(\frac{-V_{SD}}{V_T}\Bigl)}}{1+e^{\Bigl(\frac{-V_{SD}}{V_T}\Bigl)}.\frac{1}{1+2t}}$$

For a drain bias that significantly exceeds the thermal voltage, the transition function is described by:
$$F_{sat} = \frac{1}{1 + 2t}$$ The critical probability factor $t$ is determined by an average Boltzmann factor in the gate-controlled channel region and can be derived from the specific potential profile. For long-channel devices, an analytical form has been proposed, which can be found in equations (4) to (12) of the article [11].

$$ t = \frac{2.λ}{m^{2}(1-η^{2})}.\Bigl[(1-m.η).e^{-m(1-η)} -(1-m) \Bigl]$$

$$ η = 1 − tanh\Bigl(\frac{V_{SD}}{mV_T}\Bigl)$$

$$m = \frac{2.\frac{V_{Gt}}{V_T}}{1+ \sqrt{\frac{2.V_{Gt}}{{V_{crit}}}}}$$

$$ V_{Gt} = \frac{Q_{tot}}{CI}$$

Note that an increase in the transistor's overdrive leads to a spacious diffusion region and shifts the onset of saturation to a higher drain bias. At high gate bias, the necessary increase in the saturation voltage diminishes and transitions into square root growths for $V_{Gt} > V_{crit}$. Note that the saturation velocity given by Eq. (5) is only achieved for both, large $V_{SG}$ (low barrier) and large $V_{SD}$ (charge sink). Generally, the critical length for diffusion, which replaces $\lambda_{free}$ in Eq. (5), is a fraction of $L_G$ dependent on the gate voltage. The $V_{Gt}$ necessary to reach the maximum injection velocity given by the unidirectional thermal velocity decreases with $L_G$.

1. The first equation is used to calculate the average lifetime of an unstable particle. It relates the average lifetime ($t$) of an unstable particle with its mass ($m$), its binding energy ($\lambda$), and its damping factor ($\eta$). The equation is a mathematical expression of the particle's exponential decay law.

2. The second equation is used to calculate the reflection coefficient of a wave in a MOSFET (metal-oxide-semiconductor field-effect transistor). The equation relates the reflection coefficient ($\eta$) with the potential difference between the drain and the source ($V_{SD}$), the ambient temperature ($V_T$), and a device parameter ($m$).

3. The third equation is used in semiconductor devices to calculate the slope factor of a MOSFET. The slope factor is a measure of the transistor's efficiency in switching on and off quickly. The equation relates the slope factor ($m$) with the transistor's threshold voltage ($V_{GT}$), a critical voltage constant ($V_{crit}$), and the ambient temperature ($V_T$).

4. The fourth equation is used to calculate the threshold voltage of a MOSFET. The threshold voltage is the minimum voltage required to turn the transistor on. The equation relates the threshold voltage ($V_{GT}$) with the total charge ($Q_{tot}$) stored in the transistor's gate, the gate capacitance ($C$), and the current ($I$) applied to the gate.

Understanding the relationship and composition of each equation, we can implement these mathematical expressions in code to analyze the results obtained. The objective is to optimize the coefficients $J_T$, $V_{tho}$, $\delta$, $l$, $n$, $\lambda$, and $V_{crit}$, which are fundamental in modeling the equations.
Where:

- **$J_T$** `(Junction Temperature Coefficient):` Represents the variation in temperature at the junction of an electronic device, crucial for the proper design and operation of these devices.
- **$V_{tho}$** `(Threshold Voltage):` The minimum voltage required to initiate current conduction in devices like MOSFET transistors, determined by the properties of the semiconductor material.
- **$\delta$** `(Diffusion Layer Thickness):` The thickness of the doped semiconductor material layer deposited on the surface of a semiconductor substrate.
- **$l$** `(Diffusion Length):` The distance over which the doping of the semiconductor material diffuses on the substrate surface during fabrication.
- **$n$** `(Diode Ideality Coefficient):` Describes the relationship between electric current and voltage in a diode, used to calculate the voltage drop at different current levels.
- **$\lambda$** `(Voltage Drop Coefficient):` Describes the voltage drop in an electronic device relative to the electric current passing through it.
- **$V_{crit}$** `(Critical Voltage):` The maximum voltage a device can withstand without damaging its structure, determined by the properties of the semiconductor materials.

  
## Tecnologias utilizadas
- Google Colaboratory
- Python
- Curve-Fit (função de otimização)

## **COMO USAR O MODELO (VERSÃO LOCAL):**


## **COMO USAR O MODELO (VERSÃO EM NUVEM):**






