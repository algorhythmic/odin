package records

import (
	"fmt"
	"io/fs"
	"sort"
	"strings"

	"github.com/algorhythmic/odin/substrate/schemas"
	"github.com/algorhythmic/odin/substrate/strictjson"
)

// Mapping outcomes (substrate README §4.8).
const (
	MappingComplete   Outcome = "mapping_complete"
	MappingIncomplete Outcome = "mapping_incomplete"
)

// Mapping is migrations/heimdall-to-commitment.json: how heimdall's record
// types map to the commitment record (ODIN-ADR-007; Appendix A). It is a
// mapping only; the import itself is I4 (I/O contract §14 step 6; AC-38).
type Mapping struct {
	Version          int             `json:"version"`
	Status           string          `json:"status"`
	CommitmentFields []string        `json:"commitment_fields"`
	StatusMapping    []StatusMapping `json:"status_mapping"`
	Rows             []MappingRow    `json:"rows"`
}

// StatusMapping maps a heimdall task status to a commitment state.
type StatusMapping struct {
	HeimdallStatus  string `json:"heimdall_status"`
	CommitmentState string `json:"commitment_state"`
	Note            string `json:"note"`
}

// MappingRow is one heimdall record type or field group and its fate.
type MappingRow struct {
	HeimdallType    *string  `json:"heimdall_type"`
	HeimdallFields  []string `json:"heimdall_fields"`
	CommitmentField *string  `json:"commitment_field"`
	Disposition     string   `json:"disposition"`
	Gap             string   `json:"gap"`
	Source          string   `json:"source"`
}

// CommitmentFields returns the top-level property names of
// records/commitment.schema.json in the embedded contract, sorted.
func CommitmentFields() ([]string, error) {
	return CommitmentFieldsFS(schemas.FS)
}

// CommitmentFieldsFS is CommitmentFields over another file system rooted
// like substrate/schemas.
func CommitmentFieldsFS(fsys fs.FS) ([]string, error) {
	data, err := fs.ReadFile(fsys, "records/commitment.schema.json")
	if err != nil {
		return nil, err
	}
	v, err := strictjson.Decode(data)
	if err != nil {
		return nil, err
	}
	doc, _ := v.(map[string]any)
	props, ok := doc["properties"].(map[string]any)
	if !ok {
		return nil, fmt.Errorf("records: commitment schema has no properties object")
	}
	fields := make([]string, 0, len(props))
	for k := range props {
		fields = append(fields, k)
	}
	sort.Strings(fields)
	return fields, nil
}

// CoverageResult is the result of CheckMappingCoverage. Uncovered is
// always non-nil.
type CoverageResult struct {
	Outcome   Outcome
	Uncovered []string
}

// CheckMappingCoverage reports which commitment fields no mapping row
// covers (substrate README §4.8). A row covers the field its
// commitment_field names up to the first `.`; a null commitment_field
// covers nothing. Uncovered is sorted by code point.
func CheckMappingCoverage(m Mapping, fields []string) CoverageResult {
	covered := map[string]bool{}
	for _, r := range m.Rows {
		if r.CommitmentField == nil {
			continue
		}
		f, _, _ := strings.Cut(*r.CommitmentField, ".")
		covered[f] = true
	}
	uncovered := []string{}
	for _, f := range fields {
		if !covered[f] {
			uncovered = append(uncovered, f)
		}
	}
	sort.Strings(uncovered)
	if len(uncovered) == 0 {
		return CoverageResult{Outcome: MappingComplete, Uncovered: uncovered}
	}
	return CoverageResult{Outcome: MappingIncomplete, Uncovered: uncovered}
}
