# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- GiovanniHenriksen: Added ability to exclude cards from retention rate calculation by tagging them with 'exclude-retention-rate'
- GiovanniHenriksen: Added option in add-on configurations to set default number of days to simulate when opening the simulator

## [0.2.0] - 2020-03-28

### Added

- GiovanniHenriksen: Added feature to simulate new cards in addition to actual new cards collected from deck (thanks to Lucas T. over on Patreon for the suggestion!)
- GiovanniHenriksen: Set "% correct" values from actual retention stats of the selected deck
- GiovanniHenriksen: Added a config option to set the number of days to look at for retention stats calculation

### Changed

- GiovanniHenriksen: Remove "% correct" for unseen cards from controls, rather basing it off of performance on first learning step.
- Glutanimate: Optimized simulations, yielding a 25% improvement in simulation speed and 90% improvement in memory utilization
- Glutanimate: Refactored codebase, adding type annotations and clearer separation between UI code and business logic
- Glutanimate: Refactored web content to simplify future extendibility and testing outside of Anki
- GiovanniHenriksen: Optimized graph performance by limiting data points per graph to 500 by default. This can be changed through a newly introduced config option.
- Glutanimate: Added configuration docs
- Glutanimate: Display add-on version in dialogs

## [0.1.2] - 2020-03-25

### Fixed

- Glutanimate: Fixed a number of crashes that would occasionally occur on Windows due to out-of-memory errors and too frequent progress bar updates (thanks to Josh over on Patreon for the report!)

## [0.1.1] - 2020-03-25

### Added

- GiovanniHenriksen: Added option to include suspended new cards

### Changed

- GiovanniHenriksen: Tweaked graph title and UI tab order

## [0.1.0] - 2020-03-24

### Added

- Initial release of Anki-Simulator

[Unreleased]: https://github.com/olivierlacan/keep-a-changelog/compare/v0.2.0...HEAD
[Unreleased]: https://github.com/olivierlacan/keep-a-changelog/compare/v0.2.0...v0.1.2
[0.1.2]: https://github.com/olivierlacan/keep-a-changelog/compare/v0.1.2...v0.1.1
[0.1.1]: https://github.com/olivierlacan/keep-a-changelog/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/olivierlacan/keep-a-changelog/releases/tag/v0.1.0