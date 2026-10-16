package eventlog

import (
	"fmt"
	"io/fs"

	"github.com/algorhythmic/odin/substrate/schemas"
	"github.com/algorhythmic/odin/substrate/strictjson"
)

// Namespace is one entry of namespaces.json: a namespace of the event
// substrate and its single writer (I/O contract §1; ODIN-ADR-006).
type Namespace struct {
	Name      string `json:"name"`
	Writer    string `json:"writer"`
	ReadOnly  bool   `json:"read_only"`
	Content   string `json:"content"`
	Authority string `json:"authority"`
	Source    string `json:"source"`
}

// Kind is one entry of kinds.json: an Appendix C event kind with its
// default wake class and whether recovery applies it first as a control
// message (I/O contract §4, §9 step 3).
type Kind struct {
	Kind        string `json:"kind"`
	DefaultWake string `json:"default_wake"`
	Conditional bool   `json:"conditional"`
	Handling    string `json:"handling"`
	Control     bool   `json:"control"`
	Source      string `json:"source"`
}

// Catalogue holds the namespace and kind catalogues of the contract.
type Catalogue struct {
	namespaces map[string]Namespace
	kinds      map[string]Kind
}

type namespaceFile struct {
	Version    int         `json:"version"`
	Source     string      `json:"source"`
	Namespaces []Namespace `json:"namespaces"`
}

type kindFile struct {
	Version int    `json:"version"`
	Source  string `json:"source"`
	Kinds   []Kind `json:"kinds"`
}

// LoadCatalogue reads namespaces.json and kinds.json from the embedded
// contract (schemas.FS) with strict decoding. A repeated name is an error.
func LoadCatalogue() (*Catalogue, error) {
	return LoadCatalogueFS(schemas.FS)
}

// LoadCatalogueFS is LoadCatalogue over another file system rooted like
// substrate/schemas.
func LoadCatalogueFS(fsys fs.FS) (*Catalogue, error) {
	var nf namespaceFile
	if err := readStrict(fsys, "namespaces.json", &nf); err != nil {
		return nil, err
	}
	var kf kindFile
	if err := readStrict(fsys, "kinds.json", &kf); err != nil {
		return nil, err
	}
	c := &Catalogue{namespaces: map[string]Namespace{}, kinds: map[string]Kind{}}
	for _, n := range nf.Namespaces {
		if _, dup := c.namespaces[n.Name]; dup {
			return nil, fmt.Errorf("eventlog: namespaces.json repeats %q", n.Name)
		}
		c.namespaces[n.Name] = n
	}
	for _, k := range kf.Kinds {
		if _, dup := c.kinds[k.Kind]; dup {
			return nil, fmt.Errorf("eventlog: kinds.json repeats %q", k.Kind)
		}
		c.kinds[k.Kind] = k
	}
	return c, nil
}

func readStrict(fsys fs.FS, name string, v any) error {
	data, err := fs.ReadFile(fsys, name)
	if err != nil {
		return err
	}
	if err := strictjson.Unmarshal(data, v); err != nil {
		return fmt.Errorf("eventlog: %s: %w", name, err)
	}
	return nil
}

// Namespace returns the catalogue entry for name.
func (c *Catalogue) Namespace(name string) (Namespace, bool) {
	n, ok := c.namespaces[name]
	return n, ok
}

// Kind returns the catalogue entry for name.
func (c *Catalogue) Kind(name string) (Kind, bool) {
	k, ok := c.kinds[name]
	return k, ok
}

// KnownKind reports whether name is an Appendix C kind in kinds.json; an
// envelope with any other kind is `unknown_kind` (substrate README §4.1).
func (c *Catalogue) KnownKind(name string) bool {
	_, ok := c.kinds[name]
	return ok
}

// IsControl reports whether events of kind name are control messages that
// recovery applies first (I/O contract §9 step 3; substrate README §4.4).
func (c *Catalogue) IsControl(name string) bool {
	return c.kinds[name].Control
}
