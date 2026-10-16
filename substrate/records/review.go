package records

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

// Combine combines the verdicts of the reviewer positions of one round in
// service code (§10 review; ODIN-ADR-013; AC-22, AC-40; substrate README
// §4.6). The first matching rule decides:
//
//  1. any position without a verdict (unanswered, or unavailable with
//     usage.unavailable): pending — an unavailable position never waives
//     review, and pending comes before escalation;
//  2. any REJECT or INSUFFICIENT_EVIDENCE: escalated;
//  3. every result APPROVE or APPROVE_UNCHANGED: approved, with verdict
//     result APPROVE_UNCHANGED when all are unchanged, otherwise APPROVE;
//  4. otherwise (a FLAG): re_review in round 1, escalated in round 2.
func Combine(round int64, positions []Position) CombineResult {
	for _, p := range positions {
		if p.Verdict == nil {
			return CombineResult{Outcome: Pending}
		}
	}
	for _, p := range positions {
		if r := p.Verdict.Result; r == ResultReject || r == ResultInsufficientEvidence {
			return CombineResult{Outcome: Escalated}
		}
	}
	allApprove, allUnchanged := true, true
	for _, p := range positions {
		switch p.Verdict.Result {
		case ResultApproveUnchanged:
		case ResultApprove:
			allUnchanged = false
		default:
			allApprove, allUnchanged = false, false
		}
	}
	if allApprove {
		if allUnchanged {
			return CombineResult{Outcome: Approved, VerdictResult: ResultApproveUnchanged}
		}
		return CombineResult{Outcome: Approved, VerdictResult: ResultApprove}
	}
	if round == 1 {
		return CombineResult{Outcome: ReReview}
	}
	return CombineResult{Outcome: Escalated}
}
