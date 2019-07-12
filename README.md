# AutoRunUploader

Waits for a MiSeq run to finish, and then uses the REST API provided by CFIA FoodPort to upload the
sequencing run and start assembly.

### Installation

You'll need python 3.x, with packages `Gooey` and `requests` installed. Then just run `auto_run_uploader.py`, 
point the GUI to your MiSeq run folder, enter your FoodPort email and password, sit back, relax, and enjoy a margarita.