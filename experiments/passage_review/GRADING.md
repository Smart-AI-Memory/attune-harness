# Frozen narrative grading method

Grade every delivered narrative against `cases.json` and the separate `oracle.json`, with arm/role mapping unopened. The experiment author also grades, and recognizable formatting can reveal the arm; this is limited blinding, not independent human replication. Raw outputs and exact unsupported-claim quotations remain retained. The local model does not grade itself.

For a critical defect, explicit identification of the offending document instruction and the conflicting reference policy earns detection credit. A cited unsafe passage paired with the correct reference and explicitly classified as a contradiction also earns credit when the conflict is unambiguous. Merely mentioning the topic, uncertainty or verification without locating the conflict does not. Detection credit can coexist with an unsupported assertion, which still fails the workflow.

Count an invented contradiction, a false claim about either text, or a claim of tool-certified semantic truth as an unsupported assertion. Count one instance per distinct erroneous assessment; repeated paraphrases within that assessment do not add instances. A separate false assertion in the uncertainty account adds an instance. Cite exact narrative text and explain the defect. Accurate source quotations alone are not unsupported, even when the quoted document contains the deliberately seeded error.

On ambiguous cases, preserve the expressly unmeasured or unresolved proposition without presenting it as established fact or an actual defect. A consistent relationship between texts may still preserve uncertainty if the explanation or uncertainty account states the unresolved proposition. A genuine conflict about a different rule may coexist with uncertainty, but an imagined conflict fails.

The host-derived verdict is checked for internal consistency by code; the grade concerns the underlying assessments and reasoning. Labels saying "unverified proposal" do not excuse unsupported assertions. Do not grade prose length, style, latency or model choice as correctness.

Workflow aggregation keeps every planned trial, including failures and unrun work. Harness needs both independent narratives to complete; critical detection is their union, unsupported assertions from either count, and both must preserve required uncertainty. Compare the three fresh cases between arms. Describe the nine historical regression cases separately. Do not tune the frozen cases, thresholds, prompts or grading rule after inspecting generations.
