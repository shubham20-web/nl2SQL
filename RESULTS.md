#  NL2SQL System Test Results

##  Summary

* **Total Questions:** 20
* **Correct:** 17
* **Partial:** 2
* **Incorrect:** 1

**Final Score: 17/20**

---

##  Detailed Results

### Q1: How many patients do we have?

SQL: `SELECT COUNT(id) FROM patients`
Status:  Correct

---

### Q2: List all doctors and their specializations

SQL: `SELECT name, specialization FROM doctors`
Status:  Correct

---

### Q3: Show me appointments for last month

SQL uses STRFTIME and joins correctly
Status:  Correct

---

### Q4: Which doctor has the most appointments?

Uses aggregation + ordering + limit
Status:  Correct

---

### Q5: What is the total revenue?

Uses SUM correctly
Status:  Correct

---

### Q6: Show revenue by doctor

Correct joins + grouping
Status:  Correct

---

### Q7: How many cancelled appointments last quarter?

Issue: Query filters months incorrectly (hardcoded range 4–6)
Status:  Incorrect

---

### Q8: Top 5 patients by spending

Correct join + aggregation + sorting
Status:  Correct

---

### Q9: Average treatment cost by specialization

Correct multi-table join + AVG
Status:  Correct

---

### Q10: Monthly appointment count (past 6 months)

Logic mostly correct but includes extra month
Status:  Partial

---

### Q11: Which city has the most patients?

Correct GROUP BY + LIMIT
Status:  Correct

---

### Q12: Patients who visited more than 3 times

Correct HAVING clause
Status:  Correct

---

### Q13: Show unpaid invoices

Correct filter (`status != 'Paid'`)
Status:  Correct

---

### Q14: Percentage of no-show appointments

Correct percentage calculation
Status:  Correct

---

### Q15: Busiest day of the week

Correct grouping, but returns numeric day (not name)
Status:  Partial

---

### Q16: Revenue trend by month

Correct time-based aggregation
Status:  Correct

---

### Q17: Average appointment duration by doctor

Correct joins + AVG
Status:  Correct

---

### Q18: Patients with overdue invoices

Correct join + filter
Status:  Correct

---

### Q19: Compare revenue between departments

Correct grouping and aggregation
Status:  Correct

---

### Q20: Patient registration trend by month

Correct time grouping
Status: Correct

---

##  Observations

* The system performs well on:

  * Aggregations (SUM, COUNT, AVG)
  * Joins across multiple tables
  * Basic filtering and grouping

* Minor issues observed in:

  * Time-based filtering logic (Q7, Q10)
  * Formatting outputs (Q15)

---

## Conclusion

The NL2SQL system demonstrates strong capability in:

* Translating natural language into SQL queries
* Handling multi-table joins and aggregations
* Producing accurate results for most queries

Overall, the system achieves **high accuracy (85%)** with only minor improvements needed in date handling and formatting.

---
