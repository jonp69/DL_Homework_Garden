# DL Homework Garden

A Python tool for processing and filtering links from files and clipboard for use with gallery-dl. The initial development will focus on PIXIV links, but it can be extended to other sites.

## Features

- Persistent, append-only tracking of links and their metadata.
- PySide6 GUI for managing, filtering, and downloading links.
- Read links from files and clipboard.
- Filter links by user-defined rules. though a powerful user-friendly gui.
- Process links in parallel for speed.
- Display progress and results in a simple UI.
- Process links with gallery-dl.
- Skip links that take too long or download too many images. (user defined limits)
- Simple UI for input, filtering, and progress display.
- Windows compatible.

## Requirements

- Python 3.8+
- [gallery-dl](https://github.com/mikf/gallery-dl)
- Pyside6 for the UI

## Setup

1. Install Python 3.8 or newer.
2. Install gallery-dl: `pip install gallery-dl`
3. Clone this repository.

## Usage

- Run the main script to launch the UI and process links.
- Click "parse txt" to read links from files in folder or "load from clipboard" to add from the current clipboard.
- Configure filters as needed.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Filtering

The initial state with no configs does not filter anything, and thus will trigger the new filter dialog for every link.

Every time the link parser ingests a link it must correspond to a filter.

If it does not, a modal will pop up, on the modal there will be a table, with 3 columns on the left side there will be in each line a token from the link, (the initial url will be split by . and the remiander the \ or other tokens as apropriate)

On the center there will be a drop down, with options such as:

- match exactly
- match case insensitive
- match any
- match expression
- match regex
- match starts with
- match ends with
- match contains
- match not contains
- match not starts with
- match not ends with
- match not contains
- match not regex

The rightmost cell will be normaly empty except if anny of the text requiring options is selected, cause its where the expression will be input, it should be sanitized and validated before being added to the filter.

After the table there is another drop down with the action to be performed if the link matches the filter, such as:

- mark link as: to download
- mark link as: to skip
- mark link as: deleted

lastly there is a button to add the filter, if the user clicks it, the filter will be added to the list of filters, and the link will be processed again, if it matches the filter it will be added to the list of links (links.json).
If not it will trigger the modal again, until it matches a filter or the user cancels the process. if the user canvels the process, the link will not be added to the list of links and the processing of current file will halt as if did not contain more links, however the file will be marked in the Files.json and ui as Processed_halted, so thath the user can re process it again at a later time.
If the processing originally was from the clipboard, the full contents of the clipboard will be added to to a txt file in the same folder as the links.json, so thath the user can re process it later. the name of the file will be Clippboard_######.txt, where ###### is the current timestamp in seconds since epoch.

## the  main window UI

Displays a list of Filters, in front of each filter in the list there are 4 buttons:

- Edit
- Delete
- Move Up/Down
- View

- The Edit button will open the filter in the same dialog as when adding a new filter, allowing the user to edit the filter and save it.
- The Delete button will remove the filter from the list. and re process all links that match the filter, as if the filter was never there, this will not remove the links from the links.json, but will mark them as to_reprocess, so thath the program can run them agains existing filters.
- The Move Up/Down buttons will move the filter up or down in the list.
- The View button will open a dialog showing all the links that match the filter, allowing the user to see which links are affected by the filter. and allowing the user to mark them to_reprocess, to_skip, to_download or to_delete.

After the filter list there is a button to add a new filter, which will open the same dialog as when adding a new filter.

## The link processing flow

1. Read links from files or clipboard.
2. For each link, check against existing filters.
3. If a link matches a filter, apply the action (to download, to skip, or to delete).
4. If no filter matches, prompt the user to create a new filter.
5. If a filter matches, add the link to `links.json` with appropriate metadata.
5.1 If the link is marked as `deleted`, it will not be processed further but will remain in `links.json` for record-keeping.
5.2 If the link is marked as `to download`, it will be queued for processing with gallery-dl.
5.3 If the link is marked as `to skip`, it will not be processed but will remain in `links.json` untill all links are processed. and all links marked as 'to_download' are processed. when it will be downloaded. if meanwhile anny new links are added to the list, it will finish the current download and then process the links added as "to_download" and only returns to process the skipped links after all links marked as "to_download" are processed.
5.4 If the link is marked as `to reprocess`, it will be added to the list of links to be reprocessed, and will be processed again against all filters. in descending order of priority acording to the list of filters (this ordewr is changes with the Move Up/Down buttons).
5.5 if a filter wich results in a state wich is not 'deleted' processes a newly inbound link, but it already exists in the `links.json` file as `deleted: true`, this new state will be set and the 'deleted' flag will be set to `false`, so that the link can be processed again.
6. if a link whyle it is being processed, exceeds the user defined limits, a pop up will apear asking the user if they want to skip the link or continue processing it, if the user chooses to skip the link, it will be marked as `to_skip_limit` and will not be processed further.
7. If a link is marked as `to_skip_limit`, it will be added to a special list of links diplayed in a separate modal, allowing the user to see which links were skipped due to limits.wich limit was exceeded, and allowing the user to later override this decision, by trigering a dedicated gallery-dl command to download the link on a dedicated thread, so thath the main thread can continue processing other links. this modal is acessed trough a button in the main window UI, and will display all links that were skipped due to limits, allowing the user to see which links were skipped and why. If the user chooses to override the skip decision, the link will be added to a special queue for processing, and will be processed with gallery-dl in a separate thread, allowing the main thread to continue processing other links.
8. While there are no new links to be processed the program will download all links marked as `to_download` in the `links.json` file. Buttons will be added to the main window UI to allow the user to pause, resume, and stop the download process. As well as a button to skip the current link being downloaded, which halts the current download and moves it to the skipped list, allowing the user to continue processing other links.
9. The program will also display a progress bar showing the current download progress.
10. The program will log all major actions and errors to a log file for debugging and diagnostics.
)
