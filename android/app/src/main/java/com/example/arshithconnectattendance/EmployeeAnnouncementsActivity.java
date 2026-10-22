package com.example.arshithconnectattendance;

import android.content.res.ColorStateList;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.os.Build;
import android.os.Bundle;
import android.util.Log;
import android.view.View;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.ProgressBar;
import android.widget.TextView;
import android.widget.Toast;

import androidx.appcompat.app.AppCompatActivity;

import com.google.firebase.Timestamp;
import com.google.firebase.auth.FirebaseAuth;
import com.google.firebase.auth.FirebaseUser;
import com.google.firebase.firestore.DocumentSnapshot;
import com.google.firebase.firestore.FirebaseFirestore;

import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Date;
import java.util.List;
import java.util.Locale;

public class EmployeeAnnouncementsActivity extends AppCompatActivity {

    private static final String TAG = "EmployeeAnnouncements";

    private FirebaseFirestore firestore;
    private FirebaseAuth firebaseAuth;

    private LinearLayout announcementsContainer;
    private TextView tvNoAnnouncements;
    private ProgressBar progressBar;
    private LinearLayout layoutError;
    private TextView tvErrorMessage;
    private Button btnRetry;
    private TextView btnBack;
    private TextView btnRefresh;

    private String currentUid = "";
    private String currentEmail = "";
    private String currentEmployeeId = "";

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        try {
            setContentView(R.layout.activity_employee_announcements);

            firestore = FirebaseFirestore.getInstance();
            firebaseAuth = FirebaseAuth.getInstance();

            resolveCurrentUserInfo();
            initializeViews();
            setupClickListeners();
            loadAnnouncements();
        } catch (Exception e) {
            Log.e(TAG, "Fatal error initializing EmployeeAnnouncementsActivity", e);
            Toast.makeText(this, "Unable to load announcements. Please try again.", Toast.LENGTH_LONG).show();
            finish();
        }
    }

    // ============================================================
    // RESOLVE CURRENT USER INFO
    // ============================================================

    private void resolveCurrentUserInfo() {
        FirebaseUser user = firebaseAuth.getCurrentUser();
        if (user != null) {
            currentUid = user.getUid() != null ? user.getUid() : "";
            currentEmail = user.getEmail() != null ? user.getEmail().trim().toLowerCase(Locale.getDefault()) : "";

            // Query employee document to get employee_id for targeting
            if (!currentUid.isEmpty()) {
                firestore.collection("employees")
                        .document(currentUid)
                        .get()
                        .addOnSuccessListener(doc -> {
                            if (doc != null && doc.exists()) {
                                String empId = safeGetString(doc, "employee_id", "");
                                if (empId.isEmpty()) {
                                    empId = safeGetString(doc, "employeeId", "");
                                }
                                currentEmployeeId = empId.trim();
                            }
                        })
                        .addOnFailureListener(e -> {
                            Log.w(TAG, "Could not fetch employee profile for targeting: " + e.getMessage());
                        });
            }
        }
    }

    // ============================================================
    // INITIALIZE VIEWS
    // ============================================================

    private void initializeViews() {
        announcementsContainer = findViewById(R.id.announcementsContainer);
        tvNoAnnouncements = findViewById(R.id.tvNoAnnouncements);
        progressBar = findViewById(R.id.progressBar);
        layoutError = findViewById(R.id.layoutError);
        tvErrorMessage = findViewById(R.id.tvErrorMessage);
        btnRetry = findViewById(R.id.btnRetry);
        btnBack = findViewById(R.id.btnBack);
        btnRefresh = findViewById(R.id.btnRefresh);
    }

    // ============================================================
    // SETUP CLICK LISTENERS
    // ============================================================

    private void setupClickListeners() {
        if (btnBack != null) {
            btnBack.setOnClickListener(v -> finish());
        }

        if (btnRefresh != null) {
            btnRefresh.setOnClickListener(v -> loadAnnouncements());
        }

        if (btnRetry != null) {
            btnRetry.setOnClickListener(v -> loadAnnouncements());
        }
    }

    // ============================================================
    // LOAD ANNOUNCEMENTS
    // ============================================================

    private void loadAnnouncements() {
        if (isFinishing() || (Build.VERSION.SDK_INT >= Build.VERSION_CODES.JELLY_BEAN_MR1 && isDestroyed())) {
            return;
        }

        // Show loading state
        if (progressBar != null) {
            progressBar.setVisibility(View.VISIBLE);
        }
        if (layoutError != null) {
            layoutError.setVisibility(View.GONE);
        }
        if (tvNoAnnouncements != null) {
            tvNoAnnouncements.setVisibility(View.GONE);
        }

        // Query all announcements. In-memory sorting ensures robust handling of both
        // Timestamp objects and ISO date strings without Firestore composite index constraints.
        firestore.collection("announcements")
                .get()
                .addOnSuccessListener(querySnapshot -> {
                    if (isFinishing() || (Build.VERSION.SDK_INT >= Build.VERSION_CODES.JELLY_BEAN_MR1 && isDestroyed())) {
                        return;
                    }

                    if (progressBar != null) {
                        progressBar.setVisibility(View.GONE);
                    }

                    if (announcementsContainer == null) {
                        return;
                    }

                    announcementsContainer.removeAllViews();

                    if (querySnapshot == null || querySnapshot.isEmpty()) {
                        showEmptyState();
                        return;
                    }

                    List<DocumentSnapshot> filteredList = new ArrayList<>();
                    for (DocumentSnapshot document : querySnapshot.getDocuments()) {
                        if (document == null || !document.exists()) {
                            continue;
                        }

                        // Check active status
                        Boolean isActive = document.getBoolean("is_active");
                        if (isActive == null) {
                            isActive = document.getBoolean("isActive");
                        }
                        if (isActive != null && !isActive) {
                            continue; // Skip deactivated announcements
                        }

                        // Check audience authorization
                        if (isAuthorizedRecipient(document)) {
                            filteredList.add(document);
                        }
                    }

                    if (filteredList.isEmpty()) {
                        showEmptyState();
                        return;
                    }

                    // Sort newest first by parsed date
                    Collections.sort(filteredList, (d1, d2) -> {
                        Date date1 = extractDate(d1);
                        Date date2 = extractDate(d2);
                        if (date1 == null && date2 == null) return 0;
                        if (date1 == null) return 1;
                        if (date2 == null) return -1;
                        return date2.compareTo(date1); // Descending
                    });

                    // Hide empty view and render cards
                    if (tvNoAnnouncements != null) {
                        tvNoAnnouncements.setVisibility(View.GONE);
                    }

                    for (DocumentSnapshot doc : filteredList) {
                        try {
                            addAnnouncementCard(doc);
                        } catch (Exception e) {
                            Log.e(TAG, "Error rendering announcement card: " + e.getMessage(), e);
                        }
                    }
                })
                .addOnFailureListener(e -> {
                    if (isFinishing() || (Build.VERSION.SDK_INT >= Build.VERSION_CODES.JELLY_BEAN_MR1 && isDestroyed())) {
                        return;
                    }

                    if (progressBar != null) {
                        progressBar.setVisibility(View.GONE);
                    }

                    if (layoutError != null) {
                        layoutError.setVisibility(View.VISIBLE);
                        if (tvErrorMessage != null) {
                            tvErrorMessage.setText("Unable to load announcements: " + e.getLocalizedMessage());
                        }
                    } else {
                        Toast.makeText(this, "Unable to load announcements: " + e.getMessage(), Toast.LENGTH_LONG).show();
                    }
                });
    }

    private void showEmptyState() {
        if (tvNoAnnouncements != null) {
            tvNoAnnouncements.setVisibility(View.VISIBLE);
        }
        if (announcementsContainer != null) {
            announcementsContainer.removeAllViews();
        }
    }

    // ============================================================
    // AUDIENCE AUTHORIZATION CHECK
    // ============================================================

    private boolean isAuthorizedRecipient(DocumentSnapshot document) {
        String sendTo = safeGetString(document, "sendTo", "");
        if (sendTo.isEmpty()) {
            sendTo = safeGetString(document, "recipient_type", "");
        }
        if (sendTo.isEmpty()) {
            sendTo = safeGetString(document, "recipientType", "All Employees");
        }

        // If sent to all employees, or audience not specified, everyone sees it
        if ("All Employees".equalsIgnoreCase(sendTo) || "All".equalsIgnoreCase(sendTo) || sendTo.isEmpty()) {
            return true;
        }

        // Check if targeted to selected employees
        Object selectedObj = document.get("selectedEmployeeIds");
        if (selectedObj == null) {
            selectedObj = document.get("recipient_ids");
        }
        if (selectedObj == null) {
            selectedObj = document.get("recipientIds");
        }
        if (selectedObj == null) {
            selectedObj = document.get("recipients");
        }

        if (selectedObj instanceof List) {
            List<?> list = (List<?>) selectedObj;
            for (Object item : list) {
                if (item != null) {
                    String str = String.valueOf(item).trim();
                    if (!currentEmployeeId.isEmpty() && str.equalsIgnoreCase(currentEmployeeId)) {
                        return true;
                    }
                    if (!currentUid.isEmpty() && str.equalsIgnoreCase(currentUid)) {
                        return true;
                    }
                    if (!currentEmail.isEmpty() && str.equalsIgnoreCase(currentEmail)) {
                        return true;
                    }
                }
            }
            return false;
        }

        // Default to showing if target configuration is unknown
        return true;
    }

    // ============================================================
    // SAFE TYPE-TOLERANT STRING EXTRACTION
    // ============================================================

    private String safeGetString(DocumentSnapshot document, String field, String defaultVal) {
        try {
            Object val = document.get(field);
            if (val != null) {
                String str = String.valueOf(val).trim();
                return str.isEmpty() ? defaultVal : str;
            }
        } catch (Exception ignored) {}
        return defaultVal;
    }

    // ============================================================
    // SAFE TYPE-TOLERANT DATE EXTRACTION
    // ============================================================

    private Date extractDate(DocumentSnapshot document) {
        // Check primary and fallback date fields
        String[] fields = {"createdAt", "created_at", "date", "updated_at", "timestamp"};
        for (String field : fields) {
            try {
                Object raw = document.get(field);
                if (raw == null) continue;

                // 1. Firebase Timestamp
                if (raw instanceof Timestamp) {
                    return ((Timestamp) raw).toDate();
                }

                // 2. java.util.Date
                if (raw instanceof Date) {
                    return (Date) raw;
                }

                // 3. Numeric epoch timestamp
                if (raw instanceof Number) {
                    long millis = ((Number) raw).longValue();
                    if (millis < 100000000000L) { // 10 digits = seconds
                        millis *= 1000;
                    }
                    return new Date(millis);
                }

                // 4. String format parsing
                if (raw instanceof String) {
                    String str = ((String) raw).trim();
                    if (str.isEmpty()) continue;

                    // Modern Java Instant (API 26+)
                    if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                        try {
                            return Date.from(java.time.Instant.parse(str));
                        } catch (Exception ignored) {}
                    }

                    // Fallback date patterns
                    String[] patterns = {
                            "yyyy-MM-dd'T'HH:mm:ss.SSSSSSXXX",
                            "yyyy-MM-dd'T'HH:mm:ss.SSSSSS",
                            "yyyy-MM-dd'T'HH:mm:ssXXX",
                            "yyyy-MM-dd'T'HH:mm:ss.SSS'Z'",
                            "yyyy-MM-dd'T'HH:mm:ss'Z'",
                            "yyyy-MM-dd'T'HH:mm:ss",
                            "yyyy-MM-dd",
                            "dd MMM yyyy, hh:mm a",
                            "dd-MM-yyyy"
                    };

                    for (String pattern : patterns) {
                        try {
                            SimpleDateFormat sdf = new SimpleDateFormat(pattern, Locale.getDefault());
                            sdf.setLenient(true);
                            Date parsed = sdf.parse(str);
                            if (parsed != null) return parsed;
                        } catch (Exception ignored) {}
                    }
                }
            } catch (Exception ignored) {}
        }
        return null;
    }

    // ============================================================
    // FORMAT DATE FOR DISPLAY
    // ============================================================

    private String formatDate(Date date) {
        if (date == null) return "";
        try {
            return new SimpleDateFormat("dd MMM yyyy, hh:mm a", Locale.getDefault()).format(date);
        } catch (Exception e) {
            return "";
        }
    }

    // ============================================================
    // ADD ANNOUNCEMENT CARD
    // ============================================================

    private void addAnnouncementCard(DocumentSnapshot document) {
        // ========================================================
        // CARD CONTAINER
        // ========================================================

        LinearLayout card = new LinearLayout(this);
        card.setOrientation(LinearLayout.VERTICAL);

        GradientDrawable cardBg = new GradientDrawable();
        cardBg.setColor(0xFFFFFFFF);
        cardBg.setCornerRadius(dp(14));
        cardBg.setStroke(dp(1), 0xFFEDE8F5);
        card.setBackground(cardBg);

        card.setPadding(dp(20), dp(18), dp(20), dp(18));

        LinearLayout.LayoutParams cardParams = new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT
        );
        cardParams.setMargins(0, 0, 0, dp(16));
        card.setLayoutParams(cardParams);

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.LOLLIPOP) {
            card.setElevation(dp(3));
        }

        // ========================================================
        // TYPE BADGE & PRIORITY ROW
        // ========================================================

        LinearLayout headerRow = new LinearLayout(this);
        headerRow.setOrientation(LinearLayout.HORIZONTAL);
        headerRow.setLayoutParams(new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT
        ));

        TextView tvType = new TextView(this);
        String type = safeGetString(document, "type", "");
        if (type.isEmpty()) {
            type = safeGetString(document, "announcement_type", "");
        }
        if (type.isEmpty()) {
            type = safeGetString(document, "announcementType", "General");
        }

        tvType.setText(type.toUpperCase(Locale.getDefault()));
        tvType.setTextSize(11);
        tvType.setTypeface(null, Typeface.BOLD);

        // Curated badge color styling
        int badgeTextColor;
        int badgeBgColor;
        String typeLower = type.toLowerCase(Locale.getDefault());
        if (typeLower.contains("important") || typeLower.contains("urgent")) {
            badgeTextColor = 0xFFDC2626;
            badgeBgColor = 0xFFFEE2E2;
        } else if (typeLower.contains("holiday")) {
            badgeTextColor = 0xFF059669;
            badgeBgColor = 0xFFD1FAE5;
        } else if (typeLower.contains("meeting")) {
            badgeTextColor = 0xFF2563EB;
            badgeBgColor = 0xFFDBEAFE;
        } else {
            badgeTextColor = 0xFF7651E8;
            badgeBgColor = 0xFFEDE9FE;
        }

        tvType.setTextColor(badgeTextColor);
        GradientDrawable typeBadge = new GradientDrawable();
        typeBadge.setColor(badgeBgColor);
        typeBadge.setCornerRadius(dp(6));
        tvType.setBackground(typeBadge);
        tvType.setPadding(dp(10), dp(4), dp(10), dp(4));

        headerRow.addView(tvType);

        // Optional priority badge if High / Urgent
        String priority = safeGetString(document, "priority", "Normal");
        if ("High".equalsIgnoreCase(priority) || "Urgent".equalsIgnoreCase(priority)) {
            TextView tvPriority = new TextView(this);
            tvPriority.setText(priority.toUpperCase(Locale.getDefault()));
            tvPriority.setTextSize(11);
            tvPriority.setTypeface(null, Typeface.BOLD);
            tvPriority.setTextColor(0xFFB45309);

            GradientDrawable priorityBadge = new GradientDrawable();
            priorityBadge.setColor(0xFFFEF3C7);
            priorityBadge.setCornerRadius(dp(6));
            tvPriority.setBackground(priorityBadge);
            tvPriority.setPadding(dp(8), dp(4), dp(8), dp(4));

            LinearLayout.LayoutParams prioParams = new LinearLayout.LayoutParams(
                    LinearLayout.LayoutParams.WRAP_CONTENT,
                    LinearLayout.LayoutParams.WRAP_CONTENT
            );
            prioParams.setMargins(dp(8), 0, 0, 0);
            tvPriority.setLayoutParams(prioParams);

            headerRow.addView(tvPriority);
        }

        card.addView(headerRow);

        // ========================================================
        // TITLE
        // ========================================================

        TextView tvTitle = new TextView(this);
        String title = safeGetString(document, "title", "Announcement");
        tvTitle.setText(title);
        tvTitle.setTextColor(0xFF1E1736);
        tvTitle.setTextSize(18);
        tvTitle.setTypeface(null, Typeface.BOLD);

        LinearLayout.LayoutParams titleParams = new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT
        );
        titleParams.setMargins(0, dp(10), 0, 0);
        tvTitle.setLayoutParams(titleParams);

        card.addView(tvTitle);

        // ========================================================
        // MESSAGE
        // ========================================================

        TextView tvMessage = new TextView(this);
        String message = safeGetString(document, "message", "");
        tvMessage.setText(message);
        tvMessage.setTextColor(0xFF5E576A);
        tvMessage.setTextSize(14);
        tvMessage.setLineSpacing(dp(3), 1.15f);

        LinearLayout.LayoutParams messageParams = new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT
        );
        messageParams.setMargins(0, dp(8), 0, 0);
        tvMessage.setLayoutParams(messageParams);

        card.addView(tvMessage);

        // ========================================================
        // METADATA FOOTER (Author • Formatted Date)
        // ========================================================

        TextView tvFooter = new TextView(this);
        Date dateObj = extractDate(document);
        String dateFormatted = formatDate(dateObj);

        // If date could not be parsed into a Date object, fallback to raw string from document
        if (dateFormatted.isEmpty()) {
            dateFormatted = safeGetString(document, "date", "");
        }
        if (dateFormatted.isEmpty()) {
            dateFormatted = safeGetString(document, "createdAt", "");
        }

        String author = safeGetString(document, "author", "");
        if (author.isEmpty()) {
            author = safeGetString(document, "createdBy", "Admin Office");
        }

        StringBuilder footerBuilder = new StringBuilder();
        if (!author.isEmpty()) {
            footerBuilder.append("By ").append(author);
        }
        if (!dateFormatted.isEmpty()) {
            if (footerBuilder.length() > 0) {
                footerBuilder.append("  •  ");
            }
            footerBuilder.append(dateFormatted);
        }

        tvFooter.setText(footerBuilder.toString());
        tvFooter.setTextColor(0xFF918A9B);
        tvFooter.setTextSize(12);

        LinearLayout.LayoutParams footerParams = new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT
        );
        footerParams.setMargins(0, dp(14), 0, 0);
        tvFooter.setLayoutParams(footerParams);

        card.addView(tvFooter);

        // Add completed card to the container
        announcementsContainer.addView(card);
    }

    // ============================================================
    // DP CONVERTER
    // ============================================================

    private int dp(int value) {
        try {
            return (int) (value * getResources().getDisplayMetrics().density);
        } catch (Exception e) {
            return value * 2;
        }
    }

    // ============================================================
    // ON RESUME
    // ============================================================

    @Override
    protected void onResume() {
        super.onResume();
        loadAnnouncements();
    }
}