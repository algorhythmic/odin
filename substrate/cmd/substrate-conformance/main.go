// Command substrate-conformance runs the I0 fixture set through the Go
// implementation and writes the results file of substrate/schemas README
// §3: one JSON object mapping every case id to its result, keys sorted,
// two-space indentation, trailing newline.
//
//	go run ./substrate/cmd/substrate-conformance -out <path>
//
// It exits non-zero when the fixture set is defective or the file cannot be
// written. Whether results match `expected` is judged by
// scripts/compare_conformance.py (and by `go test ./...`); the command only
// reports the count of differing cases on stderr.
package main

import (
	"flag"
	"fmt"
	"os"

	"github.com/algorhythmic/odin/substrate/conformance"
)

func main() {
	out := flag.String("out", "", "path of the results JSON file to write (required)")
	flag.Parse()
	if *out == "" || flag.NArg() != 0 {
		fmt.Fprintln(os.Stderr, "usage: substrate-conformance -out <path>")
		os.Exit(2)
	}
	if err := run(*out); err != nil {
		fmt.Fprintln(os.Stderr, "substrate-conformance:", err)
		os.Exit(1)
	}
}

func run(path string) error {
	r, err := conformance.NewRunner()
	if err != nil {
		return err
	}
	cases, err := r.Cases()
	if err != nil {
		return err
	}
	results, err := r.RunAll(cases)
	if err != nil {
		return err
	}
	data, err := conformance.Encode(results)
	if err != nil {
		return err
	}
	if err := os.WriteFile(path, data, 0o644); err != nil {
		return err
	}
	mismatches, err := conformance.Compare(cases, results)
	if err != nil {
		return err
	}
	fmt.Fprintf(os.Stderr, "substrate-conformance: wrote %d results to %s; %d differ from expected\n",
		len(results), path, len(mismatches))
	return nil
}
