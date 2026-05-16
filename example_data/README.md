# QRandLab Workflow Example

This README describes a complete workflow for using the toolbox on two input files and verifying that all steps were performed correctly by checking the final set of files in the working directory.

At the very beginning, this folder already contains:

- `QRandLab_Report_20260515_174633.html` – the result of a previous, correct run of the workflow. Your goal is to reproduce an equivalent report by following the same steps.
- `BinPRNG.bin` – a random data file in **binary** format.
- `1M_PRNG_by_chacha20_V3.txt` – a random data file in **string01** format.
- `README.md` – this instruction file.

When you perform all steps correctly, you will generate the same set of result files again. Because the reference report (`QRandLab_Report_20260515_174633.html`) is already present from the previous run, you will end up with **61 files** in this directory in total.

---

## Overview of the Workflow

You start with **two input files** and run them through a sequence of:

1. Import and type assignment  
2. Validation  
3. Format conversion (to hex)  
4. Preprocessing (XOR1)  
5. Slicing  
6. Statistical tests (NIST, Borel, autocorrelation)  
7. Entropy and Dieharder tests  
8. PRNG data generation  
9. Report creation  

Correct execution of each step will produce a defined set of files. At the end, you can compare your directory contents with the file list in the table below.

---

## Step-by-Step Instructions

### 1. Import both files into the toolbox

- Import the **two base files** into the toolbox.
- After import, both files should be visible in the input table of the toolbox.

---

### 2. Set file types

Set the file types for the two input files as follows:

- One file type: `string01`
- The other file type: `binary`



---

### 3. Validate both input files

- Run the **validation** operation on both files.
- Confirm that they pass validation 

This ensures that the data is correctly formatted before any conversions or tests.

---

### 4. Convert both files to hex and tag as test

- Convert **both** original files to **hex file type**.
- Configure the toolbox to:
  - **Automatically add** the new hex files to the input table.
  - Append the suffix `_test` to the new hex file names.

After this step:

- You still have the original 2 files.
- You now have 2 additional hex (`_test`) files.

Total in input table so far: **4 files**.

---

### 5. Preprocess all four files with XOR1

- Apply the **XOR1 preprocess method** to all **four** files currently in the input table:
  - The 2 original files
  - The 2 `_test` hex files
- Configure the toolbox to:
  - **Automatically add** the preprocessed files to the input table.

After this step:

- 4 original/converted files  
- 4 new `XOR1`-processed files  

Total in input table now: **8 files**.

---

### 6. Validate all files again

- Run validation on **all 8 files** now present in the input table.
- Ensure all pass validation.

---

### 7. Slice all files into two equal-length parts

- Slice **each of the 8 files** into **2 equal-length files**:
  - For example: `filename_part1of2`, `filename_part2of2`
- **Important**: Configure the operation so that:
  - The sliced files are **saved to disk**
  - But **are not added** as new entries to the input table

After this step:

- The directory will include part1/part2 versions of each of the 8 files.
- The input table still contains only the original 8 entries.

---

### 8. Enable auto format conversion and run NIST Frequency Monobit test

- Enable **auto convert format** so that the toolbox automatically uses the proper file format for tests.
- Run the **NIST Frequency Monobit test** on **all 8 files** in the input table.

Results are expected to be stored according to the toolbox’s standard naming convention.

---

### 9. Run the Borel test (up to length 5)

- Using the same 8 files:
  - Run the **Borel test** with subsequences up to **length 5**.
- Again, auto format conversion should remain enabled.

---

### 10. Run autocorrelation test with lag 1000

- On the same 8 files:
  - Run the **autocorrelation test** with **lag = 1000**.

---

### 11. Run ENT test and save raw output

- Run the **ENT** randomness test on all 8 files.
- Configure ENT to:
  - **Save raw output** to files (these are the `*_ent_raw_*.txt` files visible in the final file list).

---

### 12. Run Dieharder test and save raw stderr/stdout for Birthday test

- Run **Dieharder** on the files with:
  - Default settings (no changes to the default Dieharder parameters)
- Additionally, for **Dieharder birthday test (id 0)**:
  - Save **raw stderr** and **stdout** outputs.
  - This produces files with names similar to  
    `*_dieharder_stderr_YYYYMMDD_HHMMSS.txt` and  
    `*_dieharder_stdout_YYYYMMDD_HHMMSS.txt`.

---

### 13. Generate 10 PRNG files

- Use **generator ID 14** with **seed 0**.
- Generate **10 PRNG files**, each containing:
  - **10,000 `uint32` numbers**
  - Stored in **string01 format** (i.e., each number as 32 bits of `0` and `1`)
- Each file will therefore contain:
  - `10,000 × 32 = 320,000` bits (`0`s and `1`s)
- Include:
  - A header in each file
  - The generator ID and seed encoded in the **file names**
  - Use the base file name: `prng_test`

The final files should look like:

- `prng_test_14_0_1.txt`  
- `prng_test_14_1_2.txt`  
- `prng_test_14_2_3.txt`  
- ...  
- `prng_test_14_9_10.txt`

---

### 14. Save the HTML report

- At the end of all operations, generate and save an **HTML report**.
- The report file name follows a pattern similar to:  
  `QRandLab_Report_YYYYMMDD_HHMMSS.html`

This HTML file summarizes the operations and results.

---

## Final File Inventory

If you have followed all steps correctly, your directory should contain exactly **61 files**.  
Below is the complete list, formatted as a table (timestamps will obviously differ):

| #  | File Name                                                         |
|----|-------------------------------------------------------------------|
| 1  | 1M_PRNG_by_chacha20_V3.txt                                        |
| 2  | 1M_PRNG_by_chacha20_V3_dieharder_stderr_YYYYMMDD_HHMMSS.txt       |
| 3  | 1M_PRNG_by_chacha20_V3_dieharder_stdout_YYYYMMDD_HHMMSS.txt       |
| 4  | 1M_PRNG_by_chacha20_V3_ent_raw_YYYYMMDD_HHMMSS.txt                |
| 5  | 1M_PRNG_by_chacha20_V3_part1of2.txt                               |
| 6  | 1M_PRNG_by_chacha20_V3_part2of2.txt                               |
| 7  | 1M_PRNG_by_chacha20_V3_test.txt                                   |
| 8  | 1M_PRNG_by_chacha20_V3_test_dieharder_stderr_YYYYMMDD_HHMMSS.txt  |
| 9  | 1M_PRNG_by_chacha20_V3_test_dieharder_stdout_YYYYMMDD_HHMMSS.txt  |
| 10 | 1M_PRNG_by_chacha20_V3_test_ent_raw_YYYYMMDD_HHMMSS.txt           |
| 11 | 1M_PRNG_by_chacha20_V3_test_part1of2.txt                          |
| 12 | 1M_PRNG_by_chacha20_V3_test_part2of2.txt                          |
| 13 | 1M_PRNG_by_chacha20_V3_test_XOR1.txt                              |
| 14 | 1M_PRNG_by_chacha20_V3_test_XOR1_dieharder_stderr_YYYYMMDD_HHMMSS.txt |
| 15 | 1M_PRNG_by_chacha20_V3_test_XOR1_dieharder_stdout_YYYYMMDD_HHMMSS.txt |
| 16 | 1M_PRNG_by_chacha20_V3_test_XOR1_ent_raw_YYYYMMDD_HHMMSS.txt      |
| 17 | 1M_PRNG_by_chacha20_V3_test_XOR1_part1of2.txt                     |
| 18 | 1M_PRNG_by_chacha20_V3_test_XOR1_part2of2.txt                     |
| 19 | 1M_PRNG_by_chacha20_V3_XOR1.txt                                   |
| 20 | 1M_PRNG_by_chacha20_V3_XOR1_dieharder_stderr_YYYYMMDD_HHMMSS.txt  |
| 21 | 1M_PRNG_by_chacha20_V3_XOR1_dieharder_stdout_YYYYMMDD_HHMMSS.txt  |
| 22 | 1M_PRNG_by_chacha20_V3_XOR1_ent_raw_YYYYMMDD_HHMMSS.txt           |
| 23 | 1M_PRNG_by_chacha20_V3_XOR1_part1of2.txt                          |
| 24 | 1M_PRNG_by_chacha20_V3_XOR1_part2of2.txt                          |
| 25 | BinPRNG.bin                                                       |
| 26 | BinPRNG_dieharder_stderr_YYYYMMDD_HHMMSS.txt                      |
| 27 | BinPRNG_dieharder_stdout_YYYYMMDD_HHMMSS.txt                      |
| 28 | BinPRNG_ent_raw_YYYYMMDD_HHMMSS.txt                               |
| 29 | BinPRNG_part1of2.bin                                              |
| 30 | BinPRNG_part2of2.bin                                              |
| 31 | BinPRNG_test.txt                                                  |
| 32 | BinPRNG_test_dieharder_stderr_YYYYMMDD_HHMMSS.txt                 |
| 33 | BinPRNG_test_dieharder_stdout_YYYYMMDD_HHMMSS.txt                 |
| 34 | BinPRNG_test_ent_raw_YYYYMMDD_HHMMSS.txt                          |
| 35 | BinPRNG_test_part1of2.txt                                         |
| 36 | BinPRNG_test_part2of2.txt                                         |
| 37 | BinPRNG_test_XOR1.txt                                             |
| 38 | BinPRNG_test_XOR1_dieharder_stderr_YYYYMMDD_HHMMSS.txt            |
| 39 | BinPRNG_test_XOR1_dieharder_stdout_YYYYMMDD_HHMMSS.txt            |
| 40 | BinPRNG_test_XOR1_ent_raw_YYYYMMDD_HHMMSS.txt                     |
| 41 | BinPRNG_test_XOR1_part1of2.txt                                    |
| 42 | BinPRNG_test_XOR1_part2of2.txt                                    |
| 43 | BinPRNG_XOR1.txt                                                  |
| 44 | BinPRNG_XOR1_dieharder_stderr_YYYYMMDD_HHMMSS.txt                 |
| 45 | BinPRNG_XOR1_dieharder_stdout_YYYYMMDD_HHMMSS.txt                 |
| 46 | BinPRNG_XOR1_ent_raw_YYYYMMDD_HHMMSS.txt                          |
| 47 | BinPRNG_XOR1_part1of2.txt                                         |
| 48 | BinPRNG_XOR1_part2of2.txt                                         |
| 49 | prng_test_14_0_1.txt                                              |
| 50 | prng_test_14_1_2.txt                                              |
| 51 | prng_test_14_2_3.txt                                              |
| 52 | prng_test_14_3_4.txt                                              |
| 53 | prng_test_14_4_5.txt                                              |
| 54 | prng_test_14_5_6.txt                                              |
| 55 | prng_test_14_6_7.txt                                              |
| 56 | prng_test_14_7_8.txt                                              |
| 57 | prng_test_14_8_9.txt                                              |
| 58 | prng_test_14_9_10.txt                                             |
| 59 | QRandLab_Report_20260515_174633.html  (reference report, already present) |
| 60 | README.md                                                         |
| 61 | QRandLab_Report_YYYYMMDD_HHMMSS.html  (Your report)               |


---

## Verification Tip (using CMD)

To quickly verify you have 61 files in this directory on Windows:
```cmd
dir /b | find /c /v ""
