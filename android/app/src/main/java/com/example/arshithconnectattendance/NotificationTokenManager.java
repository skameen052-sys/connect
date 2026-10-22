package com.example.arshithconnectattendance;

import com.google.firebase.auth.FirebaseAuth;
import com.google.firebase.auth.FirebaseUser;
import com.google.firebase.firestore.FieldValue;
import com.google.firebase.firestore.FirebaseFirestore;
import com.google.firebase.firestore.SetOptions;

import java.util.HashMap;
import java.util.Map;

public class NotificationTokenManager {

    private NotificationTokenManager() {
        // Prevent object creation
    }

    public static void saveToken(String token) {
        if (token == null || token.trim().isEmpty()) {
            return;
        }

        try {
            FirebaseAuth auth = FirebaseAuth.getInstance();
            FirebaseUser user = auth.getCurrentUser();
            if (user == null) {
                return;
            }

            String uid = user.getUid();
            FirebaseFirestore firestore = FirebaseFirestore.getInstance();

            Map<String, Object> data = new HashMap<>();
            data.put("fcmToken", token);
            data.put("fcmTokenUpdatedAt", FieldValue.serverTimestamp());

            firestore
                    .collection("employees")
                    .document(uid)
                    .set(data, SetOptions.merge())
                    .addOnFailureListener(e -> android.util.Log.e("NotificationTokenManager", "Failed to save FCM token", e));
        } catch (Exception e) {
            android.util.Log.e("NotificationTokenManager", "Exception saving FCM token", e);
        }
    }
}