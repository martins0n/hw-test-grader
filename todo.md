I want to create pipelene grader of homework assignments.

Workflow:

1. Student submits homework assignment via google classroom. (He could make multiple submissions until the deadline)
2. Every submission is downloaded to a github repository as  new commit to a specific branch associated with the student and assignment.
3. Every file is encrypted with student's key before being stored in the repository to ensure privacy.
4. A CI/CD pipeline is triggered on every new commit to the repository
5. The pipeline decrypts the files using the student's key.
6. The pipeline runs a series of automated tests and checks on the decrypted files to grade the assignment.
7. The results of the tests and checks are compiled into a report.
8. The report is sent back to the student via email or uploaded to google classroom.
9. The pipeline logs all activities and results for auditing purposes.


Possible Technologies to use:
- Google Classroom API for downloading submissions
- Python everywhere for scripting the process
- GitHub Actions
- If we need VM for submitting files to Github, i can create one. But prefer free solutions.