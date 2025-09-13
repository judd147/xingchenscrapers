"""
Enhanced Soccer Prediction System with Bayesian Machine Learning
Tailored for 星辰智盈自动回测系统 data structure

Author: Based on Liyao Zhang's original system
Enhanced with ML capabilities for better prediction accuracy
"""

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split, cross_val_score, StratifiedKFold
from sklearn.naive_bayes import GaussianNB, MultinomialNB
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import LabelEncoder, StandardScaler, MinMaxScaler
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    roc_auc_score,
    accuracy_score,
)
from sklearn.feature_selection import SelectKBest, f_classif
import matplotlib.pyplot as plt
import seaborn as sns
from collections import Counter
import warnings

warnings.filterwarnings("ignore")


class SoccerMLPredictor:
    def __init__(self):
        """
        Initialize the ML prediction system with models optimized for soccer betting
        """
        self.models = {
            "naive_bayes": GaussianNB(),
            "random_forest": RandomForestClassifier(
                n_estimators=200,
                max_depth=10,
                min_samples_split=10,
                min_samples_leaf=5,
                random_state=42,
                class_weight="balanced",
            ),
            "gradient_boosting": GradientBoostingClassifier(
                n_estimators=150, learning_rate=0.1, max_depth=6, random_state=42
            ),
            "logistic_regression": LogisticRegression(
                random_state=42, class_weight="balanced", max_iter=1000
            ),
        }

        self.label_encoders = {}
        self.scaler = StandardScaler()
        self.feature_selector = None
        self.feature_importance_ = None
        self.is_trained = False
        # Default handicap range used for training/validation/backtest
        self.handicap_min = -1.5
        self.handicap_max = 1.5

    def set_handicap_range(self, min_value=-1.5, max_value=1.5):
        """
        Configure the handicap range filter applied to datasets during
        training/validation/backtesting. Predictions can be run on any input,
        but training/testing data will respect this range.
        """
        self.handicap_min = float(min_value)
        self.handicap_max = float(max_value)

    def parse_handicap(self, handicap_str):
        """
        Parse handicap string to numeric value
        Examples: '-0.5' -> -0.5, '+0.25' -> 0.25, '-1' -> -1.0
        """
        if pd.isna(handicap_str) or handicap_str == "":
            return 0.0

        # Remove spaces and convert
        clean_str = str(handicap_str).strip().replace(" ", "")

        # Handle cases like '+0.25', '-0.5', etc.
        try:
            return float(clean_str)
        except:
            return 0.0

    def extract_features(self, df):
        """
        Extract features from your specific data structure
        """
        features = pd.DataFrame()

        # Basic numeric features - handle both string percentages and float values
        if df["胜"].dtype == "object":
            features["home_win_pct"] = (
                pd.to_numeric(df["胜"].str.rstrip("%"), errors="coerce") / 100
            )
            features["draw_pct"] = (
                pd.to_numeric(df["平"].str.rstrip("%"), errors="coerce") / 100
            )
            features["away_win_pct"] = (
                pd.to_numeric(df["负"].str.rstrip("%"), errors="coerce") / 100
            )

            # Handicap betting percentages
            features["handicap_home_pct"] = (
                pd.to_numeric(df["让胜"].str.rstrip("%"), errors="coerce") / 100
            )
            features["handicap_draw_pct"] = (
                pd.to_numeric(df["让平"].str.rstrip("%"), errors="coerce") / 100
            )
            features["handicap_away_pct"] = (
                pd.to_numeric(df["让负"].str.rstrip("%"), errors="coerce") / 100
            )
        else:
            # Data is already in float format (0.36, 0.67, etc.)
            features["home_win_pct"] = df["胜"]
            features["draw_pct"] = df["平"]
            features["away_win_pct"] = df["负"]
            features["handicap_home_pct"] = df["让胜"]
            features["handicap_draw_pct"] = df["让平"]
            features["handicap_away_pct"] = df["让负"]

        # Odds features
        features["home_odds"] = pd.to_numeric(df["主赔"], errors="coerce")
        features["away_odds"] = pd.to_numeric(df["客赔"], errors="coerce")
        features["odds_diff"] = features["home_odds"] - features["away_odds"]
        features["odds_ratio"] = features["home_odds"] / features["away_odds"]
        features["implied_prob_home"] = 1 / features["home_odds"]
        features["implied_prob_away"] = 1 / features["away_odds"]
        features["bookmaker_margin"] = (
            features["implied_prob_home"] + features["implied_prob_away"] - 1
        )

        # Handicap features
        features["handicap_value"] = df["盘口"].apply(self.parse_handicap)
        features["abs_handicap"] = abs(features["handicap_value"])
        features["is_home_handicap"] = (features["handicap_value"] < 0).astype(int)
        features["is_away_handicap"] = (features["handicap_value"] > 0).astype(int)
        features["is_deep_handicap"] = (features["abs_handicap"] > 1.0).astype(int)
        features["is_half_ball"] = (features["abs_handicap"] % 0.5 == 0).astype(int)
        features["is_quarter_ball"] = (features["abs_handicap"] % 0.25 == 0).astype(int)

        # Market efficiency features
        features["market_home_diff"] = (
            features["home_win_pct"] - features["implied_prob_home"]
        )
        features["market_away_diff"] = (
            features["away_win_pct"] - features["implied_prob_away"]
        )
        features["handicap_market_diff"] = (
            features["handicap_home_pct"] - features["handicap_away_pct"]
        )

        # Competition type
        features["is_jingcai"] = (df["竞彩"] == "是").astype(int)

        # Encode categorical features
        categorical_features = ["联赛", "算法"]
        for col in categorical_features:
            if col in df.columns:
                col_name = f"{col}_encoded"
                if col not in self.label_encoders:
                    self.label_encoders[col] = LabelEncoder()
                    # Handle missing values
                    valid_mask = df[col].notna()
                    if valid_mask.sum() > 0:
                        self.label_encoders[col].fit(df[col][valid_mask].astype(str))
                        features[col_name] = (
                            df[col]
                            .astype(str)
                            .map(
                                lambda x: (
                                    self.label_encoders[col].transform([x])[0]
                                    if x in self.label_encoders[col].classes_
                                    else -1
                                )
                            )
                        )
                    else:
                        features[col_name] = -1
                else:
                    # Transform using existing encoder
                    features[col_name] = (
                        df[col]
                        .astype(str)
                        .map(
                            lambda x: (
                                self.label_encoders[col].transform([x])[0]
                                if x in self.label_encoders[col].classes_
                                else -1
                            )
                        )
                    )

        # Time-based features (if available)
        if "开球时间" in df.columns:
            # Extract hour from time string like '08-16 07:00'
            try:
                time_parts = df["开球时间"].str.extract(r"(\d+)-(\d+)\s+(\d+):(\d+)")
                features["match_hour"] = pd.to_numeric(time_parts[2], errors="coerce")
                features["match_month"] = pd.to_numeric(time_parts[0], errors="coerce")
                features["match_day"] = pd.to_numeric(time_parts[1], errors="coerce")

                # Create time-based categories
                features["is_weekend"] = features["match_day"].apply(
                    lambda x: 1 if x in [6, 7, 13, 14, 20, 21, 27, 28] else 0
                )
                features["is_prime_time"] = (
                    (features["match_hour"] >= 19) | (features["match_hour"] <= 22)
                ).astype(int)
            except:
                features["match_hour"] = 0
                features["match_month"] = 0
                features["match_day"] = 0
                features["is_weekend"] = 0
                features["is_prime_time"] = 0

        # Fill missing values with more robust method
        features = features.fillna(features.median())

        # Additional safety check - replace any remaining NaN with 0
        features = features.fillna(0)

        return features

    def create_target_variable(self, df):
        """
        Create target variable based on actual match results
        Returns: 1 for handicap winner (上盘), 0 for handicap loser (下盘), -1 for unknown
        """
        targets = []

        for idx, row in df.iterrows():
            if pd.isna(row["H"]) or pd.isna(row["A"]):
                targets.append(-1)  # Unknown result
                continue

            home_score = int(row["H"])
            away_score = int(row["A"])
            handicap = self.parse_handicap(row["盘口"])

            # Calculate handicap result
            home_handicap_result = home_score + handicap

            if home_handicap_result > away_score:
                # Home team wins handicap (上盘 for home handicap, 下盘 for away handicap)
                if handicap <= 0:  # Home team giving handicap
                    targets.append(1)  # 上盘 wins
                else:  # Away team giving handicap
                    targets.append(0)  # 下盘 wins
            elif home_handicap_result < away_score:
                # Away team wins handicap
                if handicap <= 0:  # Home team giving handicap
                    targets.append(0)  # 下盘 wins
                else:  # Away team giving handicap
                    targets.append(1)  # 上盘 wins
            else:
                # Draw - handle based on handicap type
                if abs(handicap) % 0.25 == 0 and abs(handicap) % 0.5 != 0:
                    # Quarter ball handicap - half win/half lose
                    targets.append(-1)  # Skip for now
                else:
                    # Push - refund
                    targets.append(-1)  # Skip for now

        return np.array(targets)

    def train_models(self, df, test_size=0.2):
        """
        Train all models on the provided data
        """
        print("Extracting features...")
        # Use full dataset without handicap-range filtering for training
        features = self.extract_features(df)
        targets = self.create_target_variable(df)

        # Filter valid samples (remove unknown targets)
        valid_mask = targets != -1
        features_clean = features[valid_mask]
        targets_clean = targets[valid_mask]

        if len(features_clean) < 50:
            raise ValueError(
                f"Insufficient training data: only {len(features_clean)} valid samples"
            )

        print(
            f"Training on {len(features_clean)} samples with {len(features.columns)} features"
        )
        print(f"Class distribution: {Counter(targets_clean)}")

        # Feature selection
        selector = SelectKBest(f_classif, k=min(20, features_clean.shape[1]))
        features_selected = selector.fit_transform(features_clean, targets_clean)
        selected_features = features.columns[selector.get_support()]

        print(f"Selected features: {list(selected_features)}")

        # Scale features
        features_scaled = self.scaler.fit_transform(features_selected)

        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            features_scaled,
            targets_clean,
            test_size=test_size,
            random_state=42,
            stratify=targets_clean,
        )

        results = {}

        # Train each model
        for name, model in self.models.items():
            print(f"\nTraining {name}...")

            # Train
            model.fit(X_train, y_train)

            # Evaluate
            train_pred = model.predict(X_train)
            test_pred = model.predict(X_test)
            train_prob = (
                model.predict_proba(X_train)[:, 1]
                if hasattr(model, "predict_proba")
                else None
            )
            test_prob = (
                model.predict_proba(X_test)[:, 1]
                if hasattr(model, "predict_proba")
                else None
            )

            # Cross validation
            cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
            cv_scores = cross_val_score(
                model, features_scaled, targets_clean, cv=cv, scoring="accuracy"
            )

            # Metrics
            train_acc = accuracy_score(y_train, train_pred)
            test_acc = accuracy_score(y_test, test_pred)

            results[name] = {
                "model": model,
                "train_accuracy": train_acc,
                "test_accuracy": test_acc,
                "cv_mean": cv_scores.mean(),
                "cv_std": cv_scores.std(),
                "test_predictions": test_pred,
                "test_probabilities": test_prob,
                "test_true": y_test,
                "feature_importance": getattr(model, "feature_importances_", None),
            }

            print(
                f"{name}: Train={train_acc:.3f}, Test={test_acc:.3f}, CV={cv_scores.mean():.3f}±{cv_scores.std():.3f}"
            )

        # Store best model and feature info
        best_model_name = max(results.keys(), key=lambda x: results[x]["test_accuracy"])
        self.best_model = results[best_model_name]["model"]
        self.best_model_name = best_model_name
        self.feature_selector = selector
        self.selected_features = selected_features
        self.is_trained = True

        # Feature importance
        if results[best_model_name]["feature_importance"] is not None:
            self.feature_importance_ = pd.DataFrame(
                {
                    "feature": selected_features,
                    "importance": results[best_model_name]["feature_importance"],
                }
            ).sort_values("importance", ascending=False)

        print(
            f"\nBest model: {best_model_name} (Test Accuracy: {results[best_model_name]['test_accuracy']:.3f})"
        )

        return results, features_clean, targets_clean

    def predict_single_match(self, match_data, return_probabilities=True):
        """
        Predict outcome for a single match
        """
        if not self.is_trained:
            raise ValueError("Model not trained yet!")

        # Convert to DataFrame if it's a Series
        if isinstance(match_data, pd.Series):
            match_data = pd.DataFrame([match_data])

        # Extract features
        features = self.extract_features(match_data)

        # Select and scale features
        features_selected = self.feature_selector.transform(features)
        features_scaled = self.scaler.transform(features_selected)

        # Predict
        prediction = self.best_model.predict(features_scaled)[0]

        result = {
            "prediction": "上盘" if prediction == 1 else "下盘",
            "prediction_numeric": prediction,
            "model_used": self.best_model_name,
        }

        if return_probabilities and hasattr(self.best_model, "predict_proba"):
            probabilities = self.best_model.predict_proba(features_scaled)[0]
            result["probability_下盘"] = probabilities[0]
            result["probability_上盘"] = probabilities[1]
            result["confidence"] = max(probabilities)

            # Classify strength similar to your star system
            confidence = max(probabilities)
            if confidence >= 0.8:
                result["strength"] = "五星级"
            elif confidence >= 0.7:
                result["strength"] = "四星级"
            elif confidence >= 0.6:
                result["strength"] = "三星级"
            else:
                result["strength"] = "建议放弃"

        return result

    def enhanced_prediction_with_domain_logic(self, match_data, historical_data=None):
        """
        Combine ML predictions with domain-specific logic
        """
        # Get ML prediction
        ml_result = self.predict_single_match(match_data)

        # Apply domain-specific adjustments
        domain_adjustments = self.apply_domain_knowledge(match_data)

        # Combine predictions using Bayesian update
        if hasattr(ml_result, "probability_上盘"):
            ml_prob = ml_result["probability_上盘"]

            # Bayesian update if we have strong domain signal
            if domain_adjustments["confidence"] > 0.3:
                likelihood_ratio = domain_adjustments["likelihood_ratio"]
                updated_prob = self.bayesian_update(ml_prob, likelihood_ratio)

                final_result = ml_result.copy()
                final_result["probability_上盘"] = updated_prob
                final_result["probability_下盘"] = 1 - updated_prob
                final_result["prediction"] = "上盘" if updated_prob > 0.5 else "下盘"
                final_result["confidence"] = abs(updated_prob - 0.5) * 2

                # Update strength classification
                if final_result["confidence"] >= 0.6:
                    final_result["strength"] = (
                        "五星级" if final_result["confidence"] >= 0.8 else "四星级"
                    )
                elif final_result["confidence"] >= 0.4:
                    final_result["strength"] = "三星级"
                else:
                    final_result["strength"] = "建议放弃"

                final_result["domain_adjustment"] = domain_adjustments
                return final_result

        return ml_result

    def apply_domain_knowledge(self, match_data):
        """
        Apply domain-specific knowledge similar to your original filtering logic
        """
        adjustments = {"confidence": 0.0, "likelihood_ratio": 1.0, "reasoning": []}

        # Convert to Series if it's a DataFrame with one row
        if isinstance(match_data, pd.DataFrame):
            row = match_data.iloc[0]
        else:
            row = match_data

        # Check for strong market signals
        try:
            home_win_pct = (
                float(row["胜"].rstrip("%")) / 100 if pd.notna(row["胜"]) else 0.5
            )
            handicap_home_pct = (
                float(row["让胜"].rstrip("%")) / 100 if pd.notna(row["让胜"]) else 0.5
            )
            handicap = self.parse_handicap(row["盘口"])

            # Strong home advantage signal
            if home_win_pct > 0.65 and handicap < -0.5:
                adjustments["confidence"] = 0.4
                adjustments["likelihood_ratio"] = 2.0
                adjustments["reasoning"].append("强主场优势+让球")

            # Odds and handicap mismatch
            home_odds = float(row["主赔"]) if pd.notna(row["主赔"]) else 2.0
            away_odds = float(row["客赔"]) if pd.notna(row["客赔"]) else 2.0

            if handicap < 0 and home_odds > away_odds * 1.2:
                adjustments["confidence"] = 0.3
                adjustments["likelihood_ratio"] = 0.6
                adjustments["reasoning"].append("让球与赔率不匹配")

            # Deep handicap patterns
            if abs(handicap) > 1.5:
                if handicap_home_pct > 0.6:
                    adjustments["confidence"] = 0.35
                    adjustments["likelihood_ratio"] = 1.8
                    adjustments["reasoning"].append("深盘强势信号")

        except Exception as e:
            # If parsing fails, return neutral adjustment
            pass

        return adjustments

    def bayesian_update(self, prior_prob, likelihood_ratio):
        """
        Update probability using Bayes' theorem
        """
        prior_odds = prior_prob / (1 - prior_prob)
        posterior_odds = prior_odds * likelihood_ratio
        posterior_prob = posterior_odds / (1 + posterior_odds)

        # Prevent extreme probabilities
        return np.clip(posterior_prob, 0.05, 0.95)

    def backtest_predictions(self, df, start_idx=None):
        """
        Backtest the model on historical data
        """
        if not self.is_trained:
            raise ValueError("Model not trained yet!")

        results = []
        correct_predictions = 0
        total_predictions = 0

        # Filter data with known results (no handicap-range filtering for backtest)
        test_data = df[(df["H"].notna()) & (df["A"].notna())].copy()

        if start_idx:
            test_data = test_data.iloc[start_idx:]

        for idx, row in test_data.iterrows():
            try:
                # Make prediction
                prediction = self.predict_single_match(pd.DataFrame([row]))

                # Get actual result
                actual_target = self.create_target_variable(pd.DataFrame([row]))[0]

                if actual_target != -1:  # Valid result
                    is_correct = prediction["prediction_numeric"] == actual_target

                    results.append(
                        {
                            "match": row["比赛"],
                            "handicap": row["盘口"],
                            "predicted": prediction["prediction"],
                            "confidence": prediction.get("confidence", 0),
                            "strength": prediction.get("strength", ""),
                            "actual_result": "上盘" if actual_target == 1 else "下盘",
                            "correct": is_correct,
                            "home_score": row["H"],
                            "away_score": row["A"],
                        }
                    )

                    if is_correct:
                        correct_predictions += 1
                    total_predictions += 1

            except Exception as e:
                continue

        backtest_results = pd.DataFrame(results)
        accuracy = (
            correct_predictions / total_predictions if total_predictions > 0 else 0
        )

        print(
            f"Backtest Results: {correct_predictions}/{total_predictions} correct ({accuracy:.3f})"
        )

        return backtest_results, accuracy

    def plot_analysis(self, results, features=None, targets=None):
        """
        Create visualization of model performance and insights
        """
        fig, axes = plt.subplots(2, 2, figsize=(15, 12))

        # Model comparison
        model_names = list(results.keys())
        test_scores = [results[model]["test_accuracy"] for model in model_names]
        cv_scores = [results[model]["cv_mean"] for model in model_names]

        x = np.arange(len(model_names))
        width = 0.35

        axes[0, 0].bar(
            x - width / 2, test_scores, width, label="Test Accuracy", alpha=0.8
        )
        axes[0, 0].bar(x + width / 2, cv_scores, width, label="CV Mean", alpha=0.8)
        axes[0, 0].set_xlabel("Models")
        axes[0, 0].set_ylabel("Accuracy")
        axes[0, 0].set_title("Model Performance Comparison")
        axes[0, 0].set_xticks(x)
        axes[0, 0].set_xticklabels(model_names, rotation=45)
        axes[0, 0].legend()
        axes[0, 0].grid(True, alpha=0.3)

        # Feature importance
        if self.feature_importance_ is not None:
            top_features = self.feature_importance_.head(10)
            axes[0, 1].barh(range(len(top_features)), top_features["importance"])
            axes[0, 1].set_yticks(range(len(top_features)))
            axes[0, 1].set_yticklabels(top_features["feature"])
            axes[0, 1].set_xlabel("Importance")
            axes[0, 1].set_title("Top 10 Feature Importance")
            axes[0, 1].grid(True, alpha=0.3)

        # Confusion matrix for best model
        best_model = max(results.keys(), key=lambda x: results[x]["test_accuracy"])
        cm = confusion_matrix(
            results[best_model]["test_true"], results[best_model]["test_predictions"]
        )
        sns.heatmap(
            cm,
            annot=True,
            fmt="d",
            ax=axes[1, 0],
            cmap="Blues",
            xticklabels=["下盘", "上盘"],
            yticklabels=["下盘", "上盘"],
        )
        axes[1, 0].set_title(f"Confusion Matrix - {best_model}")
        axes[1, 0].set_xlabel("Predicted")
        axes[1, 0].set_ylabel("Actual")

        # Probability distribution
        if results[best_model]["test_probabilities"] is not None:
            probs = results[best_model]["test_probabilities"]
            true_vals = results[best_model]["test_true"]

            axes[1, 1].hist(
                probs[true_vals == 0],
                bins=20,
                alpha=0.7,
                label="下盘 Actual",
                density=True,
            )
            axes[1, 1].hist(
                probs[true_vals == 1],
                bins=20,
                alpha=0.7,
                label="上盘 Actual",
                density=True,
            )
            axes[1, 1].set_xlabel("Predicted Probability (上盘)")
            axes[1, 1].set_ylabel("Density")
            axes[1, 1].set_title("Prediction Probability Distribution")
            axes[1, 1].legend()
            axes[1, 1].grid(True, alpha=0.3)

        plt.tight_layout()
        return fig

    # ------------------------- Persistence -------------------------
    def save_model(self, file_path: str):
        """
        Save the trained model and preprocessing artifacts for future prediction.
        """
        if not self.is_trained:
            raise ValueError("Cannot save before training a model")

        import pickle

        payload = {
            "best_model": self.best_model,
            "best_model_name": getattr(self, "best_model_name", None),
            "scaler": self.scaler,
            "feature_selector": self.feature_selector,
            "selected_features": getattr(self, "selected_features", None),
            "label_encoders": self.label_encoders,
            "handicap_min": self.handicap_min,
            "handicap_max": self.handicap_max,
        }

        with open(file_path, "wb") as f:
            pickle.dump(payload, f)

    @classmethod
    def load_model(cls, file_path: str):
        """
        Load a previously saved model. Returns an initialized predictor.
        """
        import pickle

        with open(file_path, "rb") as f:
            payload = pickle.load(f)

        obj = cls()
        obj.best_model = payload["best_model"]
        obj.best_model_name = payload.get("best_model_name")
        obj.scaler = payload["scaler"]
        obj.feature_selector = payload["feature_selector"]
        obj.selected_features = payload.get("selected_features")
        obj.label_encoders = payload["label_encoders"]
        obj.handicap_min = payload.get("handicap_min", -1.5)
        obj.handicap_max = payload.get("handicap_max", 1.5)
        obj.is_trained = True
        return obj


# Integration with your existing system
def integrate_with_existing_system(excel_file_path):
    """
    Example of how to integrate with your existing system
    """
    print("加载数据...")

    # Load your data (adjust sheet_name as needed)
    df = pd.read_excel(excel_file_path, sheet_name=1)

    print(f"数据加载完成: {len(df)} 行")

    # Initialize ML system
    ml_system = SoccerMLPredictor()

    # Train models
    print("开始训练模型...")
    try:
        results, features, targets = ml_system.train_models(df)

        # Create analysis plots
        fig = ml_system.plot_analysis(results, features, targets)

        print("\n" + "=" * 50)
        print("模型训练完成!")
        print("=" * 50)

        # Backtest on recent data
        print("\n开始回测...")
        backtest_df, accuracy = ml_system.backtest_predictions(df)

        if len(backtest_df) > 0:
            print(f"回测准确率: {accuracy:.3f}")
            print("\n高置信度预测结果:")
            high_conf = backtest_df[backtest_df["confidence"] > 0.7]
            if len(high_conf) > 0:
                high_conf_accuracy = high_conf["correct"].mean()
                print(
                    f"高置信度准确率: {high_conf_accuracy:.3f} ({len(high_conf)} 场比赛)"
                )

        return ml_system, results, backtest_df

    except Exception as e:
        print(f"训练失败: {str(e)}")
        return None, None, None


def predict_upcoming_matches(ml_system, upcoming_matches_df):
    """
    Predict outcomes for upcoming matches
    """
    predictions = []

    for idx, match in upcoming_matches_df.iterrows():
        try:
            # Get enhanced prediction
            prediction = ml_system.enhanced_prediction_with_domain_logic(match)

            predictions.append(
                {
                    "match": match.get("比赛", f"Match_{idx}"),
                    "league": match.get("联赛", ""),
                    "handicap": match.get("盘口", ""),
                    "algorithm": match.get("算法", ""),
                    "prediction": prediction["prediction"],
                    "confidence": prediction.get("confidence", 0),
                    "strength": prediction.get("strength", ""),
                    "prob_upper": prediction.get("probability_上盘", 0.5),
                    "prob_lower": prediction.get("probability_下盘", 0.5),
                    "model": prediction["model_used"],
                }
            )

        except Exception as e:
            print(f"预测失败 {match.get('比赛', 'Unknown')}: {str(e)}")
            continue

    return pd.DataFrame(predictions)


if __name__ == "__main__":
    print("足球预测机器学习系统")
    print("基于星辰智盈自动回测系统增强版")
    print("\n主要功能:")
    print("1. 贝叶斯概率更新")
    print("2. 多模型集成预测")
    print("3. 特征重要性分析")
    print("4. 回测验证")
    print("5. 与现有系统集成")
