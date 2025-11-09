# Persona Data Summary - Snowflake Analysis

## ✅ CONNECTION SUCCESSFUL

Successfully connected to Snowflake and confirmed both tables exist:
- **SILAB.TEST_LAB_INTERNS.TF_Q1_PERSONA_MERCHANT_INDEXING_ALL_TIME** (37,628 rows)
- **SILAB.TEST_LAB_INTERNS.TF_Q1_PERSONA_SUBCATEGORY_INDEXING_ALL_TIME** (780 rows)

---

## 🎯 PERSONAS/AUDIENCES FOUND IN DATABASE

The following 5 personas exist in the Snowflake tables:

1. **College Basketball Fan**
2. **MLB Fans**
3. **MLS Fans**
4. **NWSL Fans**
5. **Super Bowl Fan**

---

## ⚠️ MISSING PERSONA

**"The College Football Fan"** mentioned in your request is **NOT present** in the Snowflake data.

You mentioned wanting to add "Sober Curious" to the College Football Fan persona, but this persona needs to be created first in the database.

---

## 📊 TOP CATEGORIES BY PERSONA (Top 12 shown)

### College Basketball Fan
1. Fitness *(relevant to your list)*
2. Beauty *(relevant to your list)*
3. Flowers *(relevant to your list)*
4. Tax & Legal Services *(relevant to your list)*
5. Beverages - Coffee & Tea *(relevant to your list)* - Index: 102.22
6. Home Improvement *(relevant to your list)*
7. Beverages - Alcohol *(relevant to your list)* - Index: 126.29
8. Auto Services *(relevant to your list)*
9. Sports Betting *(relevant to your list)*
10. Streaming *(relevant to your list)*
11. Food Delivery *(relevant to your list)*
12. QSR *(relevant to your list)*

**Note:** Apparel - Sneakers category exists in database but didn't appear in top 20

### MLB Fan
1. Fitness *(relevant to your list)*
2. **Sober Curious** - ❌ NOT FOUND (but "Beverages - Alcohol" exists with Index: 193.79)
3. Travel - Airlines *(relevant to your list)*
4. Youth Sports *(relevant to your list)*
5. Sports Betting *(relevant to your list)*
6. Streaming OTT *(relevant to your list)*
7. Food Delivery *(relevant to your list)*
8. QSR *(relevant to your list)*
9. Pets - Retail *(relevant to your list)*
10. Outdoor Retailers *(relevant to your list)*
11. Beverages Coffee & Tea *(relevant to your list)* - Index: 142.26
12. Gaming - Publisher *(relevant to your list)*

### Super Bowl Fan
1. Health & Fitness *(relevant to your list)* - Index: 147.62
2. Travel - airlines *(relevant to your list)*
3. Travel - Lodging & Accommodation *(relevant to your list)*
4. Sports Betting *(relevant to your list)*
5. Streaming OTT *(relevant to your list)*
6. Food Delivery *(relevant to your list)*
7. Auto *(relevant to your list)*
8. QSR *(relevant to your list)*
9. Entertainment & Music *(relevant to your list)*

### NWSL Fan
1. Boutique Fitness *(relevant to your list)* - Fitness - Workout Classes: Index: 602.44
2. Athleisure *(relevant to your list)*
3. Travel *(relevant to your list)*
4. Streaming OTT *(relevant to your list)*
5. Food Delivery *(relevant to your list)*
6. QSR *(relevant to your list)*
7. Beauty - cosmetics & skincare *(relevant to your list)*
8. Home Decor *(relevant to your list)*
9. Pets *(relevant to your list)*
10. E-tailers *(relevant to your list)*

### MLS Fan
1. Health & Fitness *(relevant to your list)*
2. Sports Betting *(relevant to your list)*
3. Streaming OTT *(relevant to your list)*
4. Food Delivery *(relevant to your list)*
5. QSR *(relevant to your list)*
6. Travel - Airlines *(relevant to your list)*
7. Dollar Stores *(relevant to your list)*
8. Theme Parks *(relevant to your list)*
9. Movie theaters *(relevant to your list)*

---

## 🚫 SOBER CURIOUS CATEGORY

**Status:** ❌ **NOT FOUND** in the current database

### What Exists Instead:
- **Beverages - Alcohol** (exists for all personas)
- **Beverages - Non-Alcoholic** (exists for all personas)
- **Beverages - Coffee & Tea** (exists for all personas)

### Index Scores for Beverage Categories:
| Audience | Beverages - Alcohol | Beverages - Non-Alcoholic | Beverages - Coffee & Tea |
|----------|-------------------|--------------------------|-------------------------|
| College Basketball Fan | 126.29 | 105.69 | 102.22 |
| MLB Fans | 193.79 | 160.80 | 142.26 |
| MLS Fans | 237.83 | 204.66 | 178.61 |
| NWSL Fans | 239.69 | 221.20 | 199.14 |
| Super Bowl Fan | 116.86 | 97.85 | 99.49 |

---

## 📋 ACTION ITEMS

1. **College Football Fan Persona:** This persona needs to be created in the Snowflake database before we can add categories to it
2. **Sober Curious Category:** This category does not exist in the database. You have two options:
   - Add "Sober Curious" as a new category to the database
   - Use existing "Beverages - Non-Alcoholic" as a proxy for sober curious behavior
3. **Data Verification:** Most of the categories you mentioned exist in the database, confirming the data is aligned with your requirements

---

## 💾 DATABASE SCHEMA

### Subcategory Table Columns:
- AUDIENCE
- COMPARISON_POPULATION
- CATEGORY
- SUBCATEGORY
- AUDIENCE_COUNT
- TOTAL_AUDIENCE_COUNT
- PERC_AUDIENCE
- AUDIENCE_TRANSACTIONS
- AUDIENCE_TOTAL_SPEND
- SPC (Spend Per Customer)
- SPP (Spend Per Purchase)
- PPC (Purchases Per Customer)
- COMPARISON_COUNT
- COMPARISON_TOTAL_COUNT
- PERC_COMPARISON
- COMPARISON_TOTAL_SPEND
- COMPARISON_SPC
- COMPARISON_SPP
- COMPARISON_PPC
- **PERC_INDEX** (main indexing metric)
- SPC_INDEX
- SPP_INDEX
- PPC_INDEX

### Merchant Table Columns:
Similar structure with MERCHANT and PARENT_MERCHANT fields added

---

## 🔄 NEXT STEPS

Would you like me to:
1. Help you add the "College Football Fan" persona to the database?
2. Help you add a "Sober Curious" category?
3. Generate visualizations comparing these personas?
4. Export this data for presentation purposes?


