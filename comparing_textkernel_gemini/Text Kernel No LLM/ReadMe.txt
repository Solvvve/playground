Thank your for using the Textkernel Product Demo for Resume Parsing!

For each file that was uploaded, a folder with that file name has been created. Inside each file folder, you will find the following documents:
 - [FileName].json (The standard parsed document as JSON)
 - [FileName].Scrubbed.json (The scrubbed version of the parsed document as JSON, more info below)
 - [FileName].xml (The standard parsed document as XML)
 - [FileName].Scrubbed.xml (The scrubbed version of the parsed document as XML, more info below)
 - [FileName].html (The HTML representation of the document text. We also support outputting the document as PDF and RTF with a simple setting in the API request)
 - [FileName] (The original file that was uploaded)

Scrubbed Documents:
The scrubbed document removes all personal data (names, addresses, phone numbers, emails, and other personal information) from the parsed document and from the document text.