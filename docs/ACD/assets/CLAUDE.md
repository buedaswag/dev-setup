# Language and toolchain
Language: Java 21, Spring Boot 3.2

# Repository structure
services/   bounded contexts - one service per domain
shared/     cross-cutting concerns - no domain logic here

# Architecture constraints
- No direct database access from handlers; all access through the repository layer
- All external calls go through a port interface; never instantiate adapters from handlers
- Payment processing is synchronous; fulfillment is always async via the event bus

# Test layout
src/test/unit/         fast, no I/O
src/test/integration/  requires running dependencies
Test class names mirror source class names with a Test suffix
