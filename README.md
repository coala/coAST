# coAST

coAST is a universal abstract syntax tree that allows to easily analyze
each programming language. Especially adding new languages should be easy and
generic.

## Goals

1. Describe languages using theoretical components, aimed at human
   comprehension, so that further understanding of concepts used by a
   language can be obtained by reading online resources rather than code.

2. Provide multiple usable levels of parse-ability, so that a file can
   be accurately split into parts which are not yet parse-able, or the
   use case has no benefit in parsing, and the parts may be modified
   and re-joined into an otherwise semantically equivalent file.

Performance and algorithmic beauty are not goals.
Reversibility, like augeas, is not a goal, as that requires a Context
Sensitive Tree.

To achieve the first goal, the primary output of this repository is a
static website which allows the reader to understand the definitions
contained here, and link to other online resources where more information
can be obtained.

Links to Wikidata, Antlr definitions, E(BNF) files, example files, will
be integral components of the definitions here.

Terminology used to describe language components will be consistent
across languages where-ever possible, and defer to terminology used
in academic literature or study guides, to make these definitions more
accessible and useful to students of language theory.

## Stages

1. Organically grow a human readable fact based database of any syntax,
   stored in YAML files, covering any language from large and complicated
   programming languages down to strings like a URL, especially focusing
   on style description which describe a subset of a language.

2. Create programs to load these definitions and convert input files
   into a universal AST, primarily for building a test suite to verify the
   language definitions are able to parse files at useful levels of detail,
   again focusing on style-defined subsets of languages which are easier
   and also more useful.

   These programs may use existing parsers, by converting the coAST
   definitions into metasyntax used by other parsing toolkits, such as BNF
   and derivatives, Antlr .g4, and augeas.

3. Standardise the definition schema once a sufficiently large number
   of language definitions have been adequately verified to determine
   the schema is able to usefully describe most concepts found in
   commonly used grammars.

## Phases

These phases will be overlapping slightly.

### Phase 1: Replace coala language definitions

The language definitions found at
https://github.com/coala/coala/tree/master/coalib/bearlib/languages
will be manually added as language definitions here, growing the schema
as necessary.  Once the import of facts is complete, a generator will
create the coala language definitions from a snapshot of the coAST language
definitions, putting the collated coAST definitions into use.

### Phase 2: Import other language definitions

There are many other collections of language definitions.
Initially the coAST definitions will only link to these external resources,
and then in the second phase those external grammars will be converted
into coAST facts, using batch import tools or manually where necessary.

In this phase tools to convert the coAST definitions into other syntax
will be needed, to round trip the language definitions, providing verification
that the imports are complete, or that partial definitions allow correct
partial parsing of those languages where complete parsing is too complex.

### Phase 3: Create language style definitions

Create declarative descriptions of common styles, such as the Google Python
coding guidelines, and Airbnb JavaScript style.

The schema for describing styles will borrow from the coala aspects
definitions, and should allow users to define their own custom styles,
however the priority will be accurately describing well established
style guides, and important features of commonly used linters of various
languages.

### Phase 4: Replace coala aspects

coala aspects development is driven by the needs of users, the complexity
of bears, and pre-existing implementation choices of coala.

For avoid these influences causing incorrect design decisions in coAST,
importing of aspects will not be considered until after style definitions
are in place.

# Authors

coAST is maintained by the [coala](https://github.com/coala)
community. Contact us on [gitter](https://gitter.im/coala/coala)!

# Licenses

The facts in this repository are inherently public domain, and are
explicitly released under the CC-0 license.
https://creativecommons.org/publicdomain/zero/1.0/

The website templates and assets included in this repository are released
under the Creative Commons Share-alike license 4.0.
https://creativecommons.org/licenses/by-sa/4.0/

Any code in this repository is to be released under the MIT license.
https://opensource.org/licenses/MIT
