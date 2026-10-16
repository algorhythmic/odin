// Package schemas embeds the I0 substrate contract: the JSON Schemas, the
// namespace and kind catalogues, the heimdall mapping and the fixture set.
// With README.md they are the single source of truth for the two
// implementations; the documents in docs/ win over them.
package schemas

import "embed"

// FS holds every contract file, rooted at this directory. Paths are the
// ones cases.json uses, for example "records/commitment.schema.json" or
// "fixtures/intake/same-dedupe-key-twice.json".
//
//go:embed *.json records fixtures migrations
var FS embed.FS
