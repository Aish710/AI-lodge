# Data verification changelog

City: **singapore**. Checked on 2026-10-17. Web-assisted: official pages were fetched and read by an AI assistant on this date. A field is source_checked only when the page states the value. Nothing here is human_verified.

All records keep `source_status: sample`. A correction is made only where an official page clearly states the value.

## Corrections (old, new, source)

| Attraction | Field | Old value | New value | Official source | What the page says |
|---|---|---|---|---|---|
| singapore_botanic_gardens | opening_hours.mon | [["05:00", "23:00"]] | [["05:00", "23:59"]] | https://sbg.nparks.gov.sg/visit/general-info/ | "Gardens 5am to 12mn daily" |
| singapore_botanic_gardens | opening_hours.tue | [["05:00", "23:00"]] | [["05:00", "23:59"]] | https://sbg.nparks.gov.sg/visit/general-info/ | "Gardens 5am to 12mn daily" |
| singapore_botanic_gardens | opening_hours.wed | [["05:00", "23:00"]] | [["05:00", "23:59"]] | https://sbg.nparks.gov.sg/visit/general-info/ | "Gardens 5am to 12mn daily" |
| singapore_botanic_gardens | opening_hours.thu | [["05:00", "23:00"]] | [["05:00", "23:59"]] | https://sbg.nparks.gov.sg/visit/general-info/ | "Gardens 5am to 12mn daily" |
| singapore_botanic_gardens | opening_hours.fri | [["05:00", "23:00"]] | [["05:00", "23:59"]] | https://sbg.nparks.gov.sg/visit/general-info/ | "Gardens 5am to 12mn daily" |
| singapore_botanic_gardens | opening_hours.sat | [["05:00", "23:00"]] | [["05:00", "23:59"]] | https://sbg.nparks.gov.sg/visit/general-info/ | "Gardens 5am to 12mn daily" |
| singapore_botanic_gardens | opening_hours.sun | [["05:00", "23:00"]] | [["05:00", "23:59"]] | https://sbg.nparks.gov.sg/visit/general-info/ | "Gardens 5am to 12mn daily" |
| national_gallery_singapore | opening_hours.tue | null | [["10:00", "19:00"]] | https://www.nationalgallery.sg/sg/en/visit/visitor-information.html | "Daily, 10am - 7pm" |
| sultan_mosque_haji_lane | opening_hours.mon | [["10:00", "18:00"]] | [["10:00", "12:00"], ["14:00", "16:00"]] | https://www.sultanmosque.sg/visitors-info/ | "Saturday to Thursday: 10.00 AM to 12.00 PM & 2.00 PM to 4.00 PM; Friday: Closed" |
| sultan_mosque_haji_lane | opening_hours.tue | [["10:00", "18:00"]] | [["10:00", "12:00"], ["14:00", "16:00"]] | https://www.sultanmosque.sg/visitors-info/ | "Saturday to Thursday: 10.00 AM to 12.00 PM & 2.00 PM to 4.00 PM; Friday: Closed" |
| sultan_mosque_haji_lane | opening_hours.wed | [["10:00", "18:00"]] | [["10:00", "12:00"], ["14:00", "16:00"]] | https://www.sultanmosque.sg/visitors-info/ | "Saturday to Thursday: 10.00 AM to 12.00 PM & 2.00 PM to 4.00 PM; Friday: Closed" |
| sultan_mosque_haji_lane | opening_hours.thu | [["10:00", "18:00"]] | [["10:00", "12:00"], ["14:00", "16:00"]] | https://www.sultanmosque.sg/visitors-info/ | "Saturday to Thursday: 10.00 AM to 12.00 PM & 2.00 PM to 4.00 PM; Friday: Closed" |
| sultan_mosque_haji_lane | opening_hours.fri | [["10:00", "18:00"]] | null | https://www.sultanmosque.sg/visitors-info/ | "Saturday to Thursday: 10.00 AM to 12.00 PM & 2.00 PM to 4.00 PM; Friday: Closed" |
| sultan_mosque_haji_lane | opening_hours.sat | [["10:00", "18:00"]] | [["10:00", "12:00"], ["14:00", "16:00"]] | https://www.sultanmosque.sg/visitors-info/ | "Saturday to Thursday: 10.00 AM to 12.00 PM & 2.00 PM to 4.00 PM; Friday: Closed" |
| sultan_mosque_haji_lane | opening_hours.sun | [["10:00", "18:00"]] | [["10:00", "12:00"], ["14:00", "16:00"]] | https://www.sultanmosque.sg/visitors-info/ | "Saturday to Thursday: 10.00 AM to 12.00 PM & 2.00 PM to 4.00 PM; Friday: Closed" |

Notes on corrections:

- singapore_botanic_gardens: Midnight is stored as 23:59 because the data format has no 24:00.
- national_gallery_singapore: The page lists no closing day, so the sample record's Tuesday closure is removed.
- sultan_mosque_haji_lane: These are the mosque's walk-in visiting hours. Haji Lane is a street whose shop hours are not covered by this page.

## Not changed, and why

- FX rate: No official page with a current SGD/USD rate could be read (the MAS pages carry no figures; the MAS data page needs interactive selection). Third-party sites claim MAS rates around 1 USD = 1.28 SGD (about 0.78 USD per SGD) in Aug-Sep 2026, but none was an official page, so the sample rate of 0.74 is unchanged and stays labelled 'sample rate, not live'.
- Travel-time calibration: No official or mainstream transit estimate for point pairs could be read with the available tools (journey planners are interactive), so no calibration was done and no constant was changed.
- Holiday notes: The Singapore city file has no holiday_notes field, so there was nothing to check.
