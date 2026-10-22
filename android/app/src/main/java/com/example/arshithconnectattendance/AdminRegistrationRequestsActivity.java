package com.example.arshithconnectattendance;

import android.content.Intent;
import android.graphics.Color;
import android.graphics.Typeface;
import android.os.Bundle;
import android.view.View;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.ProgressBar;
import android.widget.TextView;
import android.widget.Toast;

import androidx.activity.ComponentActivity;

import com.google.firebase.Timestamp;
import com.google.firebase.auth.FirebaseAuth;
import com.google.firebase.auth.FirebaseUser;
import com.google.firebase.firestore.DocumentSnapshot;
import com.google.firebase.firestore.FieldValue;
import com.google.firebase.firestore.FirebaseFirestore;
import com.google.firebase.firestore.QueryDocumentSnapshot;

import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.HashMap;
import java.util.HashSet;
import java.util.Locale;
import java.util.Map;
import java.util.Set;

public class AdminRegistrationRequestsActivity extends ComponentActivity {

    private FirebaseAuth auth;
    private FirebaseFirestore firestore;
    private FirebaseUser adminUser;

    private LinearLayout requestsContainer;
    private ProgressBar progressRequests;
    private TextView tvNoRequests;
    private Button btnRefreshRequests;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_admin_registration_requests);

        auth = FirebaseAuth.getInstance();
        firestore = FirebaseFirestore.getInstance();
        adminUser = auth.getCurrentUser();

        requestsContainer = findViewById(R.id.requestsContainer);
        progressRequests = findViewById(R.id.progressRequests);
        tvNoRequests = findViewById(R.id.tvNoRequests);
        btnRefreshRequests = findViewById(R.id.btnRefreshRequests);

        btnRefreshRequests.setOnClickListener(v -> verifyAdminAndLoad());

        if (adminUser == null) {
            goToAdminLogin();
            return;
        }

        verifyAdminAndLoad();
    }

    private void verifyAdminAndLoad() {
        FirebaseUser user = auth.getCurrentUser();

        if (user == null) {
            goToAdminLogin();
            return;
        }

        progressRequests.setVisibility(View.VISIBLE);
        btnRefreshRequests.setEnabled(false);

        firestore.collection("admins")
                .document(user.getUid())
                .get()
                .addOnSuccessListener(adminDocument -> {
                    String role = adminDocument.getString("role");

                    if (!adminDocument.exists()
                            || role == null
                            || !"admin".equalsIgnoreCase(role)) {

                        progressRequests.setVisibility(View.GONE);
                        btnRefreshRequests.setEnabled(true);

                        Toast.makeText(
                                this,
                                "Admin access denied.",
                                Toast.LENGTH_LONG
                        ).show();

                        auth.signOut();
                        goToAdminLogin();
                        return;
                    }

                    loadPendingRequests();
                })
                .addOnFailureListener(e -> {
                    progressRequests.setVisibility(View.GONE);
                    btnRefreshRequests.setEnabled(true);

                    Toast.makeText(
                            this,
                            "Could not verify admin: " + e.getMessage(),
                            Toast.LENGTH_LONG
                    ).show();
                });
    }

    private void loadPendingRequests() {
        requestsContainer.removeAllViews();
        tvNoRequests.setVisibility(View.GONE);
        progressRequests.setVisibility(View.VISIBLE);
        btnRefreshRequests.setEnabled(false);

        // Read employee documents and match "pending" without case sensitivity.
        // Firestore whereEqualTo is case-sensitive, so it can miss documents
        // whose status is stored as "Pending" instead of "pending".
        firestore.collection("employees")
                .get()
                .addOnSuccessListener(snapshot -> {
                    progressRequests.setVisibility(View.GONE);
                    btnRefreshRequests.setEnabled(true);
                    requestsContainer.removeAllViews();

                    int pendingCount = 0;
                    Set<String> seenIdentifiers = new HashSet<>();

                    for (QueryDocumentSnapshot document : snapshot) {
                        String status = document.getString("status");

                        if (status != null
                                && "pending".equalsIgnoreCase(status.trim())) {
                            String email = document.getString("email");
                            String empId = document.getString("employeeId");
                            String dedupeKey = (email != null && !email.trim().isEmpty())
                                    ? email.trim().toLowerCase()
                                    : (empId != null && !empId.trim().isEmpty() ? empId.trim() : document.getId());

                            if (!seenIdentifiers.contains(dedupeKey)) {
                                seenIdentifiers.add(dedupeKey);
                                addRequestCard(document);
                                pendingCount++;
                            }
                        }
                    }

                    tvNoRequests.setVisibility(
                            pendingCount == 0 ? View.VISIBLE : View.GONE
                    );
                })
                .addOnFailureListener(e -> {
                    progressRequests.setVisibility(View.GONE);
                    btnRefreshRequests.setEnabled(true);

                    Toast.makeText(
                            this,
                            "Unable to load requests: " + e.getMessage(),
                            Toast.LENGTH_LONG
                    ).show();
                });
    }

    private void addRequestCard(QueryDocumentSnapshot document) {
        String uid = document.getId();

        String name = getValue(document, "name", "Not provided");
        String employeeId = getValue(document, "employeeId", "Not provided");
        String email = getValue(document, "email", "Not provided");
        String phone = getValue(document, "phone", "Not provided");

        LinearLayout card = new LinearLayout(this);
        card.setOrientation(LinearLayout.VERTICAL);
        card.setPadding(dp(16), dp(16), dp(16), dp(16));
        card.setBackgroundColor(Color.WHITE);

        LinearLayout.LayoutParams cardParams =
                new LinearLayout.LayoutParams(
                        LinearLayout.LayoutParams.MATCH_PARENT,
                        LinearLayout.LayoutParams.WRAP_CONTENT
                );
        cardParams.bottomMargin = dp(14);
        card.setLayoutParams(cardParams);
        card.setElevation(dp(3));

        TextView title = new TextView(this);
        title.setText(name);
        title.setTextColor(Color.rgb(23, 43, 77));
        title.setTextSize(19);
        title.setTypeface(null, Typeface.BOLD);
        card.addView(title);

        TextView details = new TextView(this);
        details.setText(
                "Employee ID: " + employeeId
                        + "\nEmail: " + email
                        + "\nPhone: " + phone
                        + "\nStatus: Pending"
        );
        details.setTextColor(Color.rgb(71, 85, 105));
        details.setTextSize(14);
        details.setLineSpacing(dp(4), 1f);

        LinearLayout.LayoutParams detailsParams =
                new LinearLayout.LayoutParams(
                        LinearLayout.LayoutParams.MATCH_PARENT,
                        LinearLayout.LayoutParams.WRAP_CONTENT
                );
        detailsParams.topMargin = dp(10);
        card.addView(details, detailsParams);

        LinearLayout buttons = new LinearLayout(this);
        buttons.setOrientation(LinearLayout.HORIZONTAL);

        LinearLayout.LayoutParams buttonsParams =
                new LinearLayout.LayoutParams(
                        LinearLayout.LayoutParams.MATCH_PARENT,
                        LinearLayout.LayoutParams.WRAP_CONTENT
                );
        buttonsParams.topMargin = dp(14);

        Button approveButton = new Button(this);
        approveButton.setText("Approve");
        approveButton.setAllCaps(false);
        approveButton.setTextColor(Color.WHITE);
        approveButton.setBackgroundTintList(
                android.content.res.ColorStateList.valueOf(
                        Color.rgb(22, 163, 74)
                )
        );

        Button rejectButton = new Button(this);
        rejectButton.setText("Reject");
        rejectButton.setAllCaps(false);
        rejectButton.setTextColor(Color.WHITE);
        rejectButton.setBackgroundTintList(
                android.content.res.ColorStateList.valueOf(
                        Color.rgb(220, 38, 38)
                )
        );

        LinearLayout.LayoutParams buttonParams =
                new LinearLayout.LayoutParams(
                        0,
                        LinearLayout.LayoutParams.WRAP_CONTENT,
                        1f
                );
        buttonParams.setMarginEnd(dp(8));

        buttons.addView(approveButton, buttonParams);

        LinearLayout.LayoutParams rejectParams =
                new LinearLayout.LayoutParams(
                        0,
                        LinearLayout.LayoutParams.WRAP_CONTENT,
                        1f
                );
        buttons.addView(rejectButton, rejectParams);

        card.addView(buttons, buttonsParams);
        requestsContainer.addView(card);

        approveButton.setOnClickListener(v ->
                updateRequestStatus(
                        uid,
                        "approved",
                        approveButton,
                        rejectButton
                )
        );

        rejectButton.setOnClickListener(v ->
                updateRequestStatus(
                        uid,
                        "rejected",
                        approveButton,
                        rejectButton
                )
        );
    }

    private void updateRequestStatus(
            String employeeUid,
            String newStatus,
            Button approveButton,
            Button rejectButton
    ) {
        FirebaseUser currentAdmin = auth.getCurrentUser();

        if (currentAdmin == null) {
            goToAdminLogin();
            return;
        }

        approveButton.setEnabled(false);
        rejectButton.setEnabled(false);

        // Re-check admin authorization before making a decision.
        firestore.collection("admins")
                .document(currentAdmin.getUid())
                .get()
                .addOnSuccessListener(adminDocument -> {
                    String role = adminDocument.getString("role");

                    if (!adminDocument.exists()
                            || role == null
                            || !"admin".equalsIgnoreCase(role)) {
                        approveButton.setEnabled(true);
                        rejectButton.setEnabled(true);
                        Toast.makeText(
                                this,
                                "Admin access denied.",
                                Toast.LENGTH_LONG
                        ).show();
                        auth.signOut();
                        goToAdminLogin();
                        return;
                    }

                    firestore.collection("employees")
                            .document(employeeUid)
                            .get()
                            .addOnSuccessListener(employeeDocument -> {
                                String currentStatus =
                                        employeeDocument.getString("status");

                                if (!employeeDocument.exists()
                                        || !"pending".equalsIgnoreCase(
                                        currentStatus == null
                                                ? ""
                                                : currentStatus
                                )) {
                                    approveButton.setEnabled(true);
                                    rejectButton.setEnabled(true);
                                    Toast.makeText(
                                            this,
                                            "This request has already been reviewed.",
                                            Toast.LENGTH_LONG
                                    ).show();
                                    loadPendingRequests();
                                    return;
                                }

                                boolean isApproved = "approved".equalsIgnoreCase(newStatus);
                                String email = employeeDocument.getString("email");
                                String rawUid = employeeDocument.getString("uid");
                                String targetUid = (rawUid != null && !rawUid.trim().isEmpty()) ? rawUid.trim() : employeeUid;

                                Map<String, Object> updates = new HashMap<>();
                                updates.put("status", newStatus);
                                updates.put(
                                        "reviewedAt",
                                        FieldValue.serverTimestamp()
                                );
                                updates.put(
                                        "reviewedBy",
                                        currentAdmin.getUid()
                                );

                                firestore.collection("employees")
                                        .document(employeeUid)
                                        .update(updates)
                                        .addOnSuccessListener(unused -> {
                                            // Synchronize users collection for website & backend authentication
                                            Map<String, Object> userUpdates = new HashMap<>();
                                            userUpdates.put("approval_status", isApproved ? "APPROVED" : "REJECTED");
                                            userUpdates.put("is_active", isApproved);
                                            userUpdates.put("status", isApproved ? "Active" : "Rejected");
                                            userUpdates.put("reviewedAt", FieldValue.serverTimestamp());
                                            userUpdates.put("reviewedBy", currentAdmin.getUid());

                                            if (targetUid != null && !targetUid.isEmpty()) {
                                                firestore.collection("users").document(targetUid).update(userUpdates);
                                            }

                                            if (email != null && !email.trim().isEmpty()) {
                                                String cleanEmail = email.trim().toLowerCase();
                                                firestore.collection("users").whereEqualTo("email", cleanEmail).get()
                                                        .addOnSuccessListener(userDocs -> {
                                                            for (DocumentSnapshot doc : userDocs) {
                                                                doc.getReference().update(userUpdates);
                                                            }
                                                        });

                                                // Update registration_requests collection
                                                Map<String, Object> reqUpdates = new HashMap<>();
                                                reqUpdates.put("status", isApproved ? "Approved" : "Rejected");
                                                reqUpdates.put("reviewed_at", FieldValue.serverTimestamp());
                                                firestore.collection("registration_requests").whereEqualTo("email", cleanEmail).get()
                                                        .addOnSuccessListener(reqDocs -> {
                                                            for (DocumentSnapshot doc : reqDocs) {
                                                                doc.getReference().update(reqUpdates);
                                                            }
                                                        });

                                                // Update duplicate employee documents if any
                                                firestore.collection("employees").whereEqualTo("email", cleanEmail).get()
                                                        .addOnSuccessListener(empDocs -> {
                                                            for (DocumentSnapshot doc : empDocs) {
                                                                if (!doc.getId().equals(employeeUid)) {
                                                                    doc.getReference().update(updates);
                                                                }
                                                            }
                                                        });
                                            }

                                            Toast.makeText(
                                                    this,
                                                    "Registration "
                                                            + newStatus
                                                            + ".",
                                                    Toast.LENGTH_SHORT
                                            ).show();
                                            loadPendingRequests();
                                        })
                                        .addOnFailureListener(e -> {
                                            approveButton.setEnabled(true);
                                            rejectButton.setEnabled(true);
                                            Toast.makeText(
                                                    this,
                                                    "Could not update request: "
                                                            + e.getMessage(),
                                                    Toast.LENGTH_LONG
                                            ).show();
                                        });
                            })
                            .addOnFailureListener(e -> {
                                approveButton.setEnabled(true);
                                rejectButton.setEnabled(true);
                                Toast.makeText(
                                        this,
                                        "Could not check employee: "
                                                + e.getMessage(),
                                        Toast.LENGTH_LONG
                                ).show();
                            });
                })
                .addOnFailureListener(e -> {
                    approveButton.setEnabled(true);
                    rejectButton.setEnabled(true);
                    Toast.makeText(
                            this,
                            "Could not verify admin: " + e.getMessage(),
                            Toast.LENGTH_LONG
                    ).show();
                });
    }

    private String getValue(
            DocumentSnapshot document,
            String field,
            String fallback
    ) {
        String value = document.getString(field);
        return value == null || value.trim().isEmpty()
                ? fallback
                : value;
    }

    private int dp(int value) {
        return (int) (value * getResources()
                .getDisplayMetrics().density + 0.5f);
    }

    private void goToAdminLogin() {
        Intent intent = new Intent(
                this,
                AdminLoginActivity.class
        );
        intent.setFlags(
                Intent.FLAG_ACTIVITY_NEW_TASK
                        | Intent.FLAG_ACTIVITY_CLEAR_TASK
        );
        startActivity(intent);
        finish();
    }
}
