package contracts

import "fmt"

// Transition defines the narrow shared I0 rules; it does not perform effects.
func Transition(kind string, data map[string]any) (string, error) {
	switch kind {
	case "revision":
		if data["current"] == data["expected"] {
			return "apply", nil
		}
		return "stale_revision", nil
	case "dedupe":
		if data["seen"] == false {
			return "apply", nil
		}
		if data["same_content"] == true {
			return "duplicate", nil
		}
		return "identity_conflict", nil
	case "delivery":
		switch data["lookup"] {
		case "completed":
			return "delivered", nil
		case "failed":
			return "failed", nil
		case "superseded":
			return "superseded", nil
		case "absent":
			if data["idempotent"] == true && data["authorized"] == true {
				return "queued", nil
			}
		}
		return "unknown", nil
	}
	return "", fmt.Errorf("unknown transition %q", kind)
}
