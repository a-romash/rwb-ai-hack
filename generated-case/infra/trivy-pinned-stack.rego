# The case fixes the stack at Angular 20.1.6 (ТЗ, slide "Технологический стек"). Its framework
# CVEs are an accepted, documented risk of the mandated version; every other HIGH or CRITICAL
# finding still fails the scan. Remove this policy once the stack may move to a patched 20.3.x.
package trivy

import rego.v1

default ignore := false

ignore if {
	startswith(input.PkgName, "@angular/")
	input.InstalledVersion == "20.1.6"
}
