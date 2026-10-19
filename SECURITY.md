# Security and sensitive meeting data

Do not submit live attendance records, names, signatures, addresses, meeting
notes or secretariat documents to public issues, pull requests or test cases.
Store real inputs and all unpacked DOCX contents under an ignored `workspace/`
directory. Do not use a public CI runner to process confidential meetings.

The scripts process **untrusted local files**. Only run them on documents you
are authorised to process, inside an approved environment. The plugin runs
inside the user's chosen host; its data handling follows that host's terms and
the user's organisational policies, not a guarantee of offline processing.

To privately report a security concern, contact the repository owner through
an approved private channel. Do not include sensitive document contents in a
public report.
