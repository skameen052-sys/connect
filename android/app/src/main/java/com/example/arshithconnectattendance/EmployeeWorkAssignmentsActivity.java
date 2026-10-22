package com.example.arshithconnectattendance;

import android.content.res.ColorStateList;
import android.graphics.Color;
import android.graphics.Typeface;
import android.os.Bundle;
import android.view.View;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.TextView;
import android.widget.Toast;

import androidx.appcompat.app.AppCompatActivity;

import com.google.firebase.Timestamp;
import com.google.firebase.auth.FirebaseAuth;
import com.google.firebase.firestore.DocumentSnapshot;
import com.google.firebase.firestore.FirebaseFirestore;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

public class EmployeeWorkAssignmentsActivity extends AppCompatActivity {

    private FirebaseFirestore firestore;
    private FirebaseAuth auth;

    private LinearLayout assignmentsContainer;
    private TextView tvEmpty;

    private boolean isLoadingAssignments = false;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        setContentView(
                R.layout.activity_employee_work_assignments
        );

        firestore =
                FirebaseFirestore.getInstance();

        auth =
                FirebaseAuth.getInstance();

        assignmentsContainer =
                findViewById(
                        R.id.assignmentsContainer
                );

        tvEmpty =
                findViewById(
                        R.id.tvEmpty
                );

        loadAssignments();
    }

    // ============================================================
    // LOAD EMPLOYEE ASSIGNMENTS
    // ============================================================

    private void loadAssignments() {

        if (auth.getCurrentUser() == null) {
            return;
        }

        if (isLoadingAssignments) {
            return;
        }

        isLoadingAssignments = true;

        String uid =
                auth.getCurrentUser().getUid();

        /*
         * Clear existing cards.
         */
        assignmentsContainer.removeAllViews();

        tvEmpty.setVisibility(
                View.GONE
        );

        firestore
                .collection("workAssignments")
                .whereArrayContains(
                        "employeeIds",
                        uid
                )
                .get()
                .addOnSuccessListener(snapshot -> {

                    /*
                     * Always clear the container before
                     * displaying the latest Firestore data.
                     */
                    assignmentsContainer.removeAllViews();

                    List<DocumentSnapshot> assignments =
                            new ArrayList<>();

                    /*
                     * IMPORTANT:
                     *
                     * Do not display assignments whose
                     * status is Completed.
                     *
                     * The document remains in Firestore
                     * so the admin can still see the history.
                     */
                    for (DocumentSnapshot document
                            : snapshot.getDocuments()) {

                        String status =
                                document.getString(
                                        "status"
                                );

                        if (status != null
                                && status.equalsIgnoreCase(
                                "Completed"
                        )) {

                            continue;
                        }

                        assignments.add(
                                document
                        );
                    }

                    /*
                     * Sort newest assignments first.
                     */
                    Collections.sort(
                            assignments,
                            (a, b) -> {
                                Timestamp ta = null;
                                Timestamp tb = null;
                                try {
                                    Object oa = a.get("assignedAt");
                                    if (oa instanceof Timestamp) ta = (Timestamp) oa;
                                } catch (Exception ignored) {}
                                try {
                                    Object ob = b.get("assignedAt");
                                    if (ob instanceof Timestamp) tb = (Timestamp) ob;
                                } catch (Exception ignored) {}

                                if (ta == null && tb == null) {
                                    return 0;
                                }
                                if (ta == null) {
                                    return 1;
                                }
                                if (tb == null) {
                                    return -1;
                                }
                                return tb.compareTo(ta);
                            }
                    );

                    /*
                     * If all assignments are completed,
                     * show the empty message.
                     */
                    if (assignments.isEmpty()) {

                        tvEmpty.setVisibility(
                                View.VISIBLE
                        );

                        tvEmpty.setText(
                                "No active work assignments"
                        );

                        isLoadingAssignments = false;

                        return;
                    }

                    tvEmpty.setVisibility(
                            View.GONE
                    );

                    /*
                     * Display active assignments only.
                     */
                    for (DocumentSnapshot document
                            : assignments) {

                        addAssignmentCard(
                                document
                        );
                    }

                    isLoadingAssignments = false;
                })
                .addOnFailureListener(e -> {

                    isLoadingAssignments = false;

                    Toast.makeText(
                            this,
                            "Failed to load assignments: "
                                    + e.getMessage(),
                            Toast.LENGTH_LONG
                    ).show();
                });
    }

    // ============================================================
    // CREATE ASSIGNMENT CARD
    // ============================================================

    private void addAssignmentCard(
            DocumentSnapshot document
    ) {

        String title =
                document.getString("title");

        String description =
                document.getString("description");

        String priority =
                document.getString("priority");

        String dueDate =
                document.getString("dueDate");

        String status =
                document.getString("status");

        String type =
                document.getString(
                        "assignmentType"
                );

        String target;

        // --------------------------------------------------------
        // TEAM
        // --------------------------------------------------------

        if ("TEAM".equalsIgnoreCase(type)) {

            String teamName =
                    document.getString(
                            "teamName"
                    );

            if (teamName == null) {
                teamName = "Unknown Team";
            }

            target =
                    "TEAM • "
                            + teamName;

        }

        // --------------------------------------------------------
        // INDIVIDUAL
        // --------------------------------------------------------

        else {

            String employeeName =
                    document.getString(
                            "employeeName"
                    );

            if (employeeName == null) {
                employeeName = "Unknown Employee";
            }

            target =
                    "INDIVIDUAL • "
                            + employeeName;
        }

        // --------------------------------------------------------
        // DEFAULT VALUES
        // --------------------------------------------------------

        if (title == null) {
            title = "Untitled Work";
        }

        if (description == null) {
            description = "";
        }

        if (priority == null) {
            priority = "Medium";
        }

        if (dueDate == null) {
            dueDate = "";
        }

        if (status == null) {
            status = "Assigned";
        }

        // --------------------------------------------------------
        // CARD
        // --------------------------------------------------------

        LinearLayout card =
                new LinearLayout(this);

        card.setOrientation(
                LinearLayout.VERTICAL
        );

        card.setPadding(
                dp(18),
                dp(18),
                dp(18),
                dp(18)
        );

        card.setBackgroundColor(
                Color.WHITE
        );

        LinearLayout.LayoutParams params =
                new LinearLayout.LayoutParams(
                        LinearLayout.LayoutParams.MATCH_PARENT,
                        LinearLayout.LayoutParams.WRAP_CONTENT
                );

        params.setMargins(
                dp(12),
                dp(8),
                dp(12),
                dp(8)
        );

        card.setLayoutParams(params);

        // --------------------------------------------------------
        // TITLE
        // --------------------------------------------------------

        TextView tvTitle =
                new TextView(this);

        tvTitle.setText(title);

        tvTitle.setTextSize(20);

        tvTitle.setTextColor(
                Color.rgb(30, 20, 60)
        );

        tvTitle.setTypeface(
                Typeface.DEFAULT,
                Typeface.BOLD
        );

        tvTitle.setPadding(
                0,
                0,
                0,
                dp(6)
        );

        // --------------------------------------------------------
        // TARGET
        // --------------------------------------------------------

        TextView tvTarget =
                createInfo(target);

        // --------------------------------------------------------
        // DESCRIPTION
        // --------------------------------------------------------

        TextView tvDescription =
                createInfo(
                        "Description: "
                                + description
                );

        // --------------------------------------------------------
        // PRIORITY
        // --------------------------------------------------------

        TextView tvPriority =
                createInfo(
                        "Priority: "
                                + priority
                );

        // --------------------------------------------------------
        // DUE DATE
        // --------------------------------------------------------

        TextView tvDue =
                createInfo(
                        "Due Date: "
                                + (
                                dueDate.isEmpty()
                                        ? "Not set"
                                        : dueDate
                        )
                );

        // --------------------------------------------------------
        // STATUS
        // --------------------------------------------------------

        TextView tvStatus =
                createInfo(
                        "Status: "
                                + status
                );

        card.addView(tvTitle);
        card.addView(tvTarget);
        card.addView(tvDescription);
        card.addView(tvPriority);
        card.addView(tvDue);
        card.addView(tvStatus);

        // ========================================================
        // START WORK
        // ========================================================

        if ("Assigned".equalsIgnoreCase(status)) {

            Button btnStartWork =
                    new Button(this);

            btnStartWork.setText(
                    "START WORK"
            );

            btnStartWork.setTextColor(
                    Color.WHITE
            );

            btnStartWork.setBackgroundTintList(
                    ColorStateList.valueOf(
                            Color.rgb(
                                    118,
                                    81,
                                    232
                            )
                    )
            );

            LinearLayout.LayoutParams buttonParams =
                    new LinearLayout.LayoutParams(
                            LinearLayout.LayoutParams.MATCH_PARENT,
                            LinearLayout.LayoutParams.WRAP_CONTENT
                    );

            buttonParams.setMargins(
                    0,
                    dp(12),
                    0,
                    0
            );

            btnStartWork.setLayoutParams(
                    buttonParams
            );

            String assignmentId =
                    document.getId();

            btnStartWork.setOnClickListener(
                    v -> startWork(
                            assignmentId,
                            btnStartWork
                    )
            );

            card.addView(
                    btnStartWork
            );
        }

        // ========================================================
        // MARK COMPLETED
        // ========================================================

        else if (
                "In Progress".equalsIgnoreCase(status)
        ) {

            Button btnComplete =
                    new Button(this);

            btnComplete.setText(
                    "MARK COMPLETED"
            );

            btnComplete.setTextColor(
                    Color.WHITE
            );

            btnComplete.setBackgroundTintList(
                    ColorStateList.valueOf(
                            Color.rgb(
                                    52,
                                    168,
                                    83
                            )
                    )
            );

            LinearLayout.LayoutParams buttonParams =
                    new LinearLayout.LayoutParams(
                            LinearLayout.LayoutParams.MATCH_PARENT,
                            LinearLayout.LayoutParams.WRAP_CONTENT
                    );

            buttonParams.setMargins(
                    0,
                    dp(12),
                    0,
                    0
            );

            btnComplete.setLayoutParams(
                    buttonParams
            );

            String assignmentId =
                    document.getId();

            btnComplete.setOnClickListener(
                    v -> completeWork(
                            assignmentId,
                            btnComplete
                    )
            );

            card.addView(
                    btnComplete
            );
        }

        assignmentsContainer.addView(
                card
        );
    }

    // ============================================================
    // START WORK
    // ============================================================

    private void startWork(
            String assignmentId,
            Button button
    ) {

        if (auth.getCurrentUser() == null) {
            return;
        }

        button.setEnabled(false);

        firestore
                .collection("workAssignments")
                .document(assignmentId)
                .update(
                        "status",
                        "In Progress",
                        "startedAt",
                        Timestamp.now()
                )
                .addOnSuccessListener(
                        unused -> {

                            Toast.makeText(
                                    this,
                                    "Work started",
                                    Toast.LENGTH_SHORT
                            ).show();

                            loadAssignments();
                        }
                )
                .addOnFailureListener(
                        e -> {

                            button.setEnabled(true);

                            Toast.makeText(
                                    this,
                                    "Unable to start work: "
                                            + e.getMessage(),
                                    Toast.LENGTH_LONG
                            ).show();
                        }
                );
    }

    // ============================================================
    // COMPLETE WORK
    // ============================================================

    private void completeWork(
            String assignmentId,
            Button button
    ) {

        if (auth.getCurrentUser() == null) {
            return;
        }

        button.setEnabled(false);

        firestore
                .collection("workAssignments")
                .document(assignmentId)
                .update(
                        "status",
                        "Completed",
                        "completedAt",
                        Timestamp.now()
                )
                .addOnSuccessListener(
                        unused -> {

                            Toast.makeText(
                                    this,
                                    "Work completed",
                                    Toast.LENGTH_SHORT
                            ).show();

                            /*
                             * Reload the list.
                             *
                             * The completed assignment will
                             * now be filtered out and disappear
                             * from the employee screen.
                             */
                            loadAssignments();
                        }
                )
                .addOnFailureListener(
                        e -> {

                            button.setEnabled(true);

                            Toast.makeText(
                                    this,
                                    "Unable to complete work: "
                                            + e.getMessage(),
                                    Toast.LENGTH_LONG
                            ).show();
                        }
                );
    }

    // ============================================================
    // CREATE INFO TEXT
    // ============================================================

    private TextView createInfo(
            String text
    ) {

        TextView tv =
                new TextView(this);

        tv.setText(text);

        tv.setTextSize(14);

        tv.setTextColor(
                Color.DKGRAY
        );

        tv.setPadding(
                0,
                dp(5),
                0,
                dp(5)
        );

        return tv;
    }

    // ============================================================
    // DP
    // ============================================================

    private int dp(int value) {

        return (int) (
                value
                        * getResources()
                        .getDisplayMetrics()
                        .density
        );
    }
}