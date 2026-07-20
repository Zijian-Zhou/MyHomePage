# Paper Introduction Markdown Framework

> Purpose: A writing template for the Introduction section of a research paper. Replace bracketed placeholders with the concrete problem, method, evidence, and claims of the current paper.

## 1. Research Background

- Research area: [e.g., 3D point cloud classification, adversarial robustness, defense methods, test-time adaptation]
- Practical motivation: [Explain why the problem matters and where it appears in real applications]
- Current trend: [Summarize relevant directions such as robust training, input purification, dynamic routing, multi-branch defense, or risk-aware selection]

Suggested writing flow:

1. Introduce the broad task and application setting in 1-2 sentences.
2. Explain the reliability or robustness risk that limits deployment.
3. Narrow the discussion to the specific problem addressed by this paper.

## 2. Problem Definition and Challenges

This paper studies: [Define the core problem in one sentence].

The main challenges are:

- Challenge 1: [e.g., attack distributions are diverse, and a single defense branch cannot adapt reliably]
- Challenge 2: [e.g., an enhancement branch may improve hard-attack samples but harm originally correct samples]
- Challenge 3: [e.g., router selection must be separated from heldout test evaluation to avoid leakage]
- Challenge 4: [e.g., cross-dataset transfer is limited by sparse positive-gain samples or feature shift]

Points to elaborate:

- Why existing methods do not directly solve these challenges.
- How these challenges affect experimental claims.
- How the paper defines the tradeoff between robustness gain and safety preservation.

## 3. Limitations of Existing Methods

Existing work can be grouped into:

- Category 1: [e.g., adversarial training]
- Category 2: [e.g., input preprocessing or purification]
- Category 3: [e.g., test-time augmentation or dynamic selection]
- Category 4: [e.g., feature-based or risk-aware routing]

Common limitations:

- They often lack fine-grained treatment of different attack or perturbation states.
- Enhancement branches can be useful under hard attacks but harmful under clean, rotation, nudge, or other benign shifts.
- Average accuracy alone can hide sample-level gain/harm tradeoffs.
- Some evaluation pipelines risk mixing selection evidence with heldout test outcomes.

## 4. Core Idea

This paper proposes: [Method name].

The core intuition is: [Explain the method in 1-2 sentences].

The method consists of:

- Component 1: [e.g., no-label feature bank / risk feature extraction]
- Component 2: [e.g., safety-aware router / gain predictor]
- Component 3: [e.g., veto mechanism / cap mechanism / branch selection]
- Component 4: [e.g., validation-only selection, frozen thresholds, heldout test evaluation]

Key design principles:

- Do not use test labels or test correctness for router selection.
- Model potential gain and harm risk separately.
- Prioritize non-degradation before pursuing hard-attack gains.
- Diagnose cross-dataset failure modes instead of overstating claims.

## 5. Overview of Experimental Findings

The main findings are:

- On [Dataset A], [method name] achieves [main gain or safety result].
- On [Dataset B], the method shows [no-harm / weak-gain / limited-transfer behavior].
- Under [attack type], the results reveal [key observation].
- Ablations show that [core component] is necessary for the final result.
- Diagnostic analyses indicate that [failure or boundary behavior] is mainly caused by [reason].

Avoid writing only that the method is "consistently better." Clearly separate:

- Claims supported by the main protocol.
- Diagnostic-only observations.
- Limitations under specific datasets, attacks, or transfer settings.

## 6. Contributions

The contributions can be summarized as:

1. We propose [method/framework name] for [task objective].
2. We design [key mechanism] to balance robustness gain and safety under [constraints].
3. We establish a strict [validation/test/leakage audit] protocol to support reproducible claims.
4. We provide sample-level gain/harm analysis, ablations, and cross-dataset diagnostics to explain the method's operating boundary.

## 7. Paper Organization

The rest of the paper is organized as follows:

- Section 2 reviews related work.
- Section 3 defines the problem setting and evaluation protocol.
- Section 4 introduces the proposed method.
- Section 5 presents experiments, ablations, and diagnostic analyses.
- Section 6 discusses limitations and future work.
- Section 7 concludes the paper.

## 8. Editable Introduction Draft Skeleton

[Field/task] is important for [application setting], but reliable deployment remains limited by [key risk]. In particular, under [specific data/model/attack setting], a model must not only resist strong attacks but also avoid introducing additional errors on clean or mildly perturbed samples.

Existing methods typically improve robustness through [existing strategy]. However, they remain limited in [specific challenge]: on the one hand, [enhancement/defense branch] may provide gains on hard attacks; on the other hand, the same branch can cause harmful prediction changes on other samples. Therefore, maximizing average accuracy alone is insufficient for supporting safe deployment.

To address this issue, we propose [method name], a [method description] framework. It uses [input feature / no-label feature / risk signal] to estimate the potential gain and harm risk of candidate branches, and applies [routing / gating / veto] to decide whether the enhancement branch should be activated. The selection process relies only on validation data, while the heldout test split is used only for final evaluation, avoiding test leakage.

Experiments show that [method name] achieves [core result] on [Dataset A] while preserving [safety dimension]. On [Dataset B], the method exhibits [boundary result], and further diagnostics show that the gap is mainly due to [reason]. These results support a cautious dataset-conditional claim: [recommended claim].

Our contributions are as follows: [List 3-4 contributions].
