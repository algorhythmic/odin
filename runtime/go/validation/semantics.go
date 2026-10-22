package validation

import "fmt"

const MaxSafeInteger int64 = 9007199254740991

// ClassifyIntake is a pure I0 check. Saga sequences are increasing, not dense.
func ClassifyIntake(lastSequence, incomingSequence *int64, dedupeSeen bool) (string, error) {
	for _, value := range []*int64{lastSequence, incomingSequence} {
		if value != nil && (*value < 0 || *value > MaxSafeInteger) {
			return "", fmt.Errorf("sequence outside safe nonnegative range: %d", *value)
		}
	}
	if dedupeSeen || (lastSequence != nil && incomingSequence != nil && *incomingSequence <= *lastSequence) {
		return "duplicate", nil
	}
	return "new", nil
}

func CheckRevision(expected, actual int64) (string, error) {
	if expected < 1 || actual < 1 || expected > MaxSafeInteger || actual > MaxSafeInteger {
		return "", fmt.Errorf("revision outside safe positive range")
	}
	if expected != actual {
		return "stale_revision", nil
	}
	return "ok", nil
}

func CheckOwnership(expectedGeneration, actualGeneration int64) (string, error) {
	if expectedGeneration < 1 || actualGeneration < 1 || expectedGeneration > MaxSafeInteger || actualGeneration > MaxSafeInteger {
		return "", fmt.Errorf("ownership generation outside safe positive range")
	}
	if expectedGeneration != actualGeneration {
		return "stale_owner", nil
	}
	return "ok", nil
}

type Reconciliation struct {
	State  string `json:"state"`
	Action string `json:"action"`
}

// ReconcileOperation does not dispatch. It expresses the safe decision after
// consulting Saga's operation lookup; a retry still requires revalidation.
func ReconcileOperation(status string) (Reconciliation, error) {
	switch status {
	case "completed":
		return Reconciliation{"delivered", "none"}, nil
	case "pending":
		return Reconciliation{"unknown", "wait"}, nil
	case "failed":
		return Reconciliation{"failed", "none"}, nil
	case "superseded":
		return Reconciliation{"superseded", "none"}, nil
	case "absent":
		return Reconciliation{"unknown", "retry_after_revalidation"}, nil
	case "unknown_expired":
		return Reconciliation{"unknown", "surface_to_operator"}, nil
	default:
		return Reconciliation{}, fmt.Errorf("unknown operation status %q", status)
	}
}
