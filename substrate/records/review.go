package records

import "fmt"

// Review combination outcomes (substrate README §4.6).
const (
	Approved  Outcome = "approved"
	Escalated Outcome = "escalated"
	Pending   Outcome = "pending"
	ReReview  Outcome = "re_review"
)

// Verdict results (§10).
const (
	ResultApproveUnchanged     = "APPROVE_UNCHANGED"
	ResultApprove              = "APPROVE"
	ResultFlag                 = "FLAG"
	ResultReject               = "REJECT"
	ResultInsufficientEvidence = "INSUFFICIENT_EVIDENCE"
)

// CombineResult is the result of Combine. VerdictResult is set only when
// Outcome is Approved.
type CombineResult struct {
	Outcome       Outcome
	VerdictResult string
}

// Combine combines the verdicts of the two reviewer positions of one round
// in service code (§10 review; ODIN-ADR-013; AC-22, AC-40; substrate README
// §4.6). It refuses, with an error, anything but round 1 or 2 and exactly
// two positions, one "a" and one "b": it never approves with fewer. The
// first matching rule decides:
//
//  1. any REJECT or INSUFFICIENT_EVIDENCE: escalated — unconditional
//     (§10, Appendix A, ODIN-ADR-013), so a rejection reaches the operator
//     even while the other position is unanswered or unavailable;
//  2. any position without a verdict (unanswered, or unavailable with
//     usage.unavailable): pending — an unavailable position never waives
//     review;
//  3. both results APPROVE or APPROVE_UNCHANGED: approved, with verdict
//     result APPROVE_UNCHANGED when both are unchanged, otherwise APPROVE;
//  4. FLAG: two FLAGs agree that the artifact needs the operator (pinned
//     Saga contract ADM-7), so escalated in any round; a FLAG with an
//     approval is a disagreement, so re_review in round 1 and escalated in
//     round 2. This rule is Odin's provisional reading pending the open
//     guidance-result question (DECISIONS.md issue X-7).
func Combine(round int64, positions []Position) (CombineResult, error) {
	if round != 1 && round != 2 {
		return CombineResult{}, fmt.Errorf("review round %d: a review has round 1 or 2", round)
	}
	if len(positions) != 2 {
		return CombineResult{}, fmt.Errorf("%d positions: a review combines exactly two positions", len(positions))
	}
	if a, b := positions[0].Position, positions[1].Position; !(a == "a" && b == "b" || a == "b" && b == "a") {
		return CombineResult{}, fmt.Errorf("positions %q and %q: a review combines one position a and one position b", a, b)
	}
	for _, p := range positions {
		if p.Verdict == nil {
			continue
		}
		if r := p.Verdict.Result; r == ResultReject || r == ResultInsufficientEvidence {
			return CombineResult{Outcome: Escalated}, nil
		}
	}
	for _, p := range positions {
		if p.Verdict == nil {
			return CombineResult{Outcome: Pending}, nil
		}
	}
	allUnchanged, flags := true, 0
	for _, p := range positions {
		switch p.Verdict.Result {
		case ResultApproveUnchanged:
		case ResultApprove:
			allUnchanged = false
		case ResultFlag:
			flags++
		default:
			return CombineResult{}, fmt.Errorf("verdict result %q is not a §10 result", p.Verdict.Result)
		}
	}
	switch {
	case flags == 0 && allUnchanged:
		return CombineResult{Outcome: Approved, VerdictResult: ResultApproveUnchanged}, nil
	case flags == 0:
		return CombineResult{Outcome: Approved, VerdictResult: ResultApprove}, nil
	case flags == 2 || round == 2:
		return CombineResult{Outcome: Escalated}, nil
	}
	return CombineResult{Outcome: ReReview}, nil
}
