workplan_backlog

## PURPOSE ##
This file serves as a location to make note of potential fixes, changes, implementations, additions, upgrades, redesigns, adjustments, and any other sensible tasks.
You will read from the backlog, if you pick a task from the backlog, you will remove it from the backlog and add it to the `workplan.md`
As you are working, you will outline things you find for future agents to address, and you will document them here in this file.
This file serves many purposes:
A) For you (the codex ai agent) to keep track of things you find, possible updates we can implement, and suggestions you have. 
B) Future AI agents to pick up on tasks, know what to do, where to do it, how to do it, etc. 
C) Self documenting AI upgrade implementation. 
	-	By writing your findings here, and adding them to this 'to-do list' of sorts, you are not only documenting what you notice as you work, but you also instruct future AI agents on tasks they should perform.
D) A way of developing long term goal tracking and implementation.
E) Temporally based growth and development. 
	-	This project is being worked on soley by AI agents, with a single human doing back and forth hands on testing. 
	-	The human cannot keep track of all possible fixes, changes, and ideas. So this also serves as a way to help the human with their growth plans. 
	
## NOTES ##
*All upgrades, updates, fixes, etc. Should all be aligned with good scientific practises, all sources should be cited correctly.*
*Document as much as you can throughout our varitey of documentation locations/sources. Read as much as you can, dig through directories to find information.*
*Use all documentation to your advantage. We have laid out a lot of foundations for you to learn from and build upon.*
*Maintain good UI practices. Check functionality on all tasks performed, to ensure all parts of our code work properly as we make changes.*
*Continue to expand and add documentation to our in app display as we progress.*
*The documentation section of the program serves several purposes, mostly for AI-learning/training in the form of long form documentation to train AI agents each time they work on our program. But also for humans who use the application to refer to in app documentation related to spectroscopy, physics, astronomy, astrochemistry, etc. and learn in great detail about each*
*Always make sure all tasks performed are scientificaly accurate in all fields.*
*Adjust/update documentation and all relevant files, scripts, tests, UI elements, history, Atlas entries, brain files, tools, specs, reference sources, user and dev documentation, as updates/adjustments are made such that all information stays current and up to date as we develop*

## Backlog ## 
- [ ] Replace digitised JWST tables with calibrated FITS ingestion and provenance links once the pipeline can access MAST data.
- [ ] Expand the spectral-line catalogue beyond hydrogen (e.g., He I, O III, Fe II) with citations and regression coverage.
- [ ] Integrate IR functional-group heuristics into importer header parsing for automated axis validation.
- [ ] Prototype a native extension hook (e.g., `pybind11`/C++) for high-throughput spectral transforms and document the Windows build toolchain.
- [ ] Capture refreshed IR overlay screenshots for `docs/user/reference_data.md` after anchored rendering changes land on Windows builds.
- [ ] Publish Markdown summaries for historic QA reviews (e.g., launch-debugging PDF) with citations and source links.
- [ ] Reconcile `reports/roadmap.md` with the current importer, overlay, and documentation backlog, adding longer-term research goals.
- [ ] Schedule a documentation sweep covering reference data, patch notes, and roadmap updates with acceptance criteria tied to regression tests.