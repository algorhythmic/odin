package main

import (
	"fmt"
	"odin.local/odin/internal/contracts"
	"os"
)

func main() {
	suite, err := contracts.Load("schemas")
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
	count, err := suite.Fixtures("fixtures/contracts.json")
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
	fmt.Printf("PASS: Go validates %d shared contract cases.\n", count)
}
