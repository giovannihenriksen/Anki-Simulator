# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.2] - 2021-08-07

### Fixed
- GiovanniHenriksen: Fixed a bug that would cause a crash or incorrect simulations for users with a number of learning or lapse steps greater than 9 (Thanks to baderj for reporting)
- RumovZ: Fixed crash for Anki version 2.1.45 and higher. Thanks to AnKingMed for reporting.

## [1.1.1] - 2021-02-21

### Added
- GiovanniHenriksen: Graph tooltip now shows the day number

### Fixed
- GiovanniHenriksen: Usage of decimals in learning and lapse steps is now allowed
- GiovanniHenriksen: Fixed bug where the average number of cards was not correct if the number of days simulated was larger than the max number of data points

## [1.1] - 2021-01-30

### Added

- GiovanniHenriksen: Added more stats to the graph, including percentage mature

## [1.0.2] - 2020-07-21

### Fixed
- Glutanimate: Fixed compatability issue for Anki 2.1.28
- Glutanimate: Fixed graph background color in night mode for alternate Anki builds (2.1.28-alternate)

## [1.0.1] - 2020-05-25

### Changed
- GiovanniHenriksen: Changed Y-axis label to 'Number of repetitions'
- GiovanniHenriksen: Updated manual

### Fixed
- GiovanniHenriksen: Fixed a bug where the chart would not show when the deck title contained an apostrophe
- GiovanniHenriksen: Fixed a bug where the simulator would load learning/lapse steps incorrectly in the latest version of Anki (2.1.26)


## [1.0.0] - 2020-04-02

### Added

- GiovanniHenriksen: Added ability to exclude cards from retention rate calculation by tagging them with 'exclude-retention-rate'
- GiovanniHenriksen: Added option in add-on configurations to set default number of days to simulate when opening the simulator
- GiovanniHenriksen: Added manual

### Changed

- Glutanimate: Configuration values are now checked for their validity. This also enables users to utilize @Arthur-Milchior's [Graphical form to change add-on configuration](https://ankiweb.net/shared/info/1014777615) add-on.
- GiovanniHenriksen: Retention rates that have a 95% CI margin of error > 5 % are now excluded. This prevents unrealistic retention rates from showing up. Instead, the default retention rate is set. 

### Fixed

- GiovanniHenriksen: Fixed bug that prevented textfields from being edited/selected
- GiovanniHenriksen: Improved simulator scheduler to very closely match the actual scheduler, including Anki's V2 scheduler.
- Glutanimate: Fixed an issue where invalid intervals in the user's collection would prevent the add-on from working (thanks to Samer over on Patreon for the report)
- Glutanimate: Fixed support for switching Anki user profiles
- GiovanniHenriksen: Fixed dialog background color on older versions of Anki


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
