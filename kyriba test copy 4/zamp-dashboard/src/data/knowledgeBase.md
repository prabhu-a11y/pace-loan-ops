# AUTO LOAN OPERATIONS – STANDARD OPERATING PROCEDURE
## End-to-End Loan Processing Workflow (US Banks)

---

## 1. PURPOSE OF THIS SOP
This document outlines the end-to-end operational process followed when a customer applies for an Auto Loan, covering:
- Application intake
- Verification and validation checks
- Credit and collateral evaluation
- Decisioning and pricing
- Approval, rejection, booking, and funding
- Post-funding compliance and audit

**This SOP is designed to ensure:**
- Consistent decision-making
- Compliance with regulatory requirements
- Operational accuracy
- Audit readiness

---

## 2. SCOPE
This SOP applies to:
- Direct and indirect auto loans
- Retail consumer auto financing
- Loans originated through dealers or bank channels

---

## 3. OVERALL PROCESS FLOW
The auto loan process is divided into four major stages:
1. **Borrower Application & Pre-Approval**
2. **Vehicle Identification & Collateral Validation**
3. **Credit Decisioning, Pricing & Communication**
4. **Loan Booking, Funding & Audit**

---

### STAGE 1: BORROWER APPLICATION & PRE-APPROVAL

#### Step 1: Application Intake & Data Capture
**Objective:** Capture and standardize all borrower application data required to initiate loan processing.
**Actions Performed:**
- Receive application from borrower or dealer
- Capture borrower details: Full legal name, DOB, Address, Employment, Income.
- Assign a unique application reference number.
- Normalize data formats (dates, addresses, numeric fields).

**Key Checks:** Mandatory fields completeness, valid data formats, duplicate application detection.
**Outcome:** Application accepted OR flagged for missing/invalid information.

#### Step 2: Eligibility Pre-Check
**Objective:** Ensure the applicant meets basic eligibility requirements before deeper evaluation.
**Rules Applied:** Minimum legal age, State-level lending eligibility, Employment and residency requirements.
**Outcome:** Eligible → proceed | Ineligible → application declined with reason.

#### Step 3: Identity & Fraud Verification
**Objective:** Verify borrower identity and screen for fraud and sanctions risk.
**Checks Performed:**
- Identity verification using provided documents.
- Cross-verification of paystubs and bank statements.
- OFAC sanctions screening.
- Fraud risk indicators review.

**Decision Rules:** Positive sanctions match → automatic rejection | Identity mismatch or high fraud risk → refer for review.
**Outcome:** Identity verified OR additional documentation requested OR application rejected.

#### Step 4: Credit Data Retrieval
**Objective:** Establish borrower creditworthiness using bureau data.
**Actions Performed:** Retrieve credit report, extract applicable FICO score, review tradelines and delinquency history.
**Outcome:** Credit profile established OR application referred.

#### Step 5: Conditional Pre-Approval Assessment
**Objective:** Determine an indicative loan offer based on borrower affordability.
**Calculations:** Debt-to-Income (DTI), Payment-to-Income (PTI), Credit utilization.
**Rules Applied:** Maximum DTI thresholds, Product-specific affordability limits.
**Outcome:** Conditional pre-approval issued OR application referred/declined.

---

### STAGE 2: VEHICLE IDENTIFICATION & COLLATERAL VALIDATION

#### Step 6: Vehicle Identification
**Objective:** Validate vehicle details proposed as loan collateral using VIN.
**Outcome:** Vehicle profile created OR vehicle data flagged for mismatch.

#### Step 7: Collateral Eligibility Review
**Objective:** Ensure the vehicle meets collateral policy requirements (Age, Mileage, Title criteria).
**Outcome:** Collateral approved OR application referred/declined.

#### Step 8: Vehicle Valuation & Loan-to-Value (LTV) Calculation
**Objective:** Assess collateral value and exposure risk.
**Actions Performed:** Retrieve industry valuations, normalize based on condition, calculate LTV ratio.
**Rules Applied:** Maximum allowable LTV thresholds.
**Outcome:** Collateral valuation accepted OR loan terms adjusted/declined.

---

### STAGE 3: DECISIONING, PRICING & COMMUNICATION

#### Step 9: Credit Risk Assessment
**Objective:** Assess overall credit risk using internal risk models (Expected Loss, Risk Grade).

#### Step 10: Credit Policy Decisioning
**Objective:** Arrive at a final loan decision (Approve, Counter-offer, Decline, Refer).

#### Step 11: Risk-Based Pricing
**Objective:** Determine final loan pricing (Interest rate, Loan term) based on approved risk tier.

#### Step 12: Customer Communication & Stipulations
**Objective:** Issue notification, provide disclosures, and list required stipulations (Insurance, Docs).

---

### STAGE 4: LOAN BOOKING, FUNDING & AUDIT

#### Step 13: Document Collection & Verification
**Objective:** Final review of Retail Installment Contract, Insurance, Title application, and Odometer disclosure.

#### Step 14: Loan Booking & Funding
**Objective:** Finalize loan in OS, execute e-signatures, and disburse funds to dealer/seller.

#### Step 15: Post-Funding Monitoring
**Objective:** Monitor title receipt confirmation, insurance validity, and SLA adherence.

#### Step 16: Final Reconciliation & Audit
**Objective:** Re-screen sanctions, reconcile funding, compile complete loan case file, and archive records.

---

## 4. FINAL OUTCOMES
1. **Approved & Funded**
2. **Approved but Withdrawn**
3. **Declined**
4. **Cancelled**

---

## 5. GOVERNANCE & OVERSIGHT
- All steps are logged for absolute auditability.
- Exceptions require documented supervisor approval.
- Policy updates are version-controlled and regulator-safe.
