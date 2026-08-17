# Initial Domain Vocabulary

These terms are project-local definitions for a fictional model, not insurer-specific terminology.

| Term | Definition |
| --- | --- |
| Policy | A fictional in-force contract represented by immutable lifecycle events |
| Policy event | A versioned fact that occurred at a recorded event time |
| Event type | A stable namespaced value that selects the payload contract for an event |
| Payload | Strictly structured fictional facts whose schema is selected by the event type |
| Active | The initial fictional policy status before a grace-period or terminal outcome transition |
| Grace period | A fictional nonterminal status indicating that payment is overdue under later simulator rules |
| Observation date | The as-of time at which state and model features are constructed |
| Prediction horizon | The period after an observation date in which an outcome label is evaluated |
| Lapse | A fictional termination outcome associated with nonpayment after configured conditions |
| Surrender | A fictional policyholder-initiated termination outcome |
| Outcome event | A lapse or surrender fact from which a later observation process may derive a label |
| Conservation case | A review item containing point-in-time evidence, allowed actions, and a human decision |
| Risk score | A calibrated estimate for a defined outcome and horizon; not an action decision |
| Eligibility rule | A deterministic condition that allows, blocks, or requires review of an action |
| Audit replay | Reconstruction of the facts, versions, recommendation, and decision known at a prior time |
