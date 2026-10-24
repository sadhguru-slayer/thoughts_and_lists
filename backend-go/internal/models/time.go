package models

import (
	"fmt"
	"strings"
	"time"
)

// FlexibleTime handles unmarshaling dates in RFC3339, ISO8601 without timezone, or simple date formats.
type FlexibleTime struct {
	time.Time
}

func (ft *FlexibleTime) UnmarshalJSON(b []byte) error {
	s := strings.Trim(string(b), "\"")
	if s == "null" || s == "" {
		ft.Time = time.Time{}
		return nil
	}

	formats := []string{
		time.RFC3339Nano,
		time.RFC3339,
		"2006-01-02T15:04:05",
		"2006-01-02T15:04",
		"2006-01-02 15:04:05",
		"2006-01-02 15:04",
		"2006-01-02",
	}

	for _, layout := range formats {
		if t, err := time.Parse(layout, s); err == nil {
			ft.Time = t
			return nil
		}
	}

	return fmt.Errorf("cannot parse %q as FlexibleTime", s)
}

func (ft FlexibleTime) MarshalJSON() ([]byte, error) {
	if ft.IsZero() {
		return []byte("null"), nil
	}
	return []byte(fmt.Sprintf("%q", ft.Format(time.RFC3339))), nil
}
