from difflib import SequenceMatcher
from typing import Dict, List

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


class ErrorMatcher:
    def __init__(self, catalog_df: pd.DataFrame):
        self.catalog_df = catalog_df.reset_index(drop=True)
        self._vectorizer = TfidfVectorizer(ngram_range=(1, 2), lowercase=True)
        corpus = self.catalog_df.apply(self._row_to_text, axis=1).tolist()
        self._matrix = self._vectorizer.fit_transform(corpus)

    @staticmethod
    def _row_to_text(row: pd.Series) -> str:
        return " ".join(
            [
                str(row.get("error_type", "")),
                str(row.get("error_pattern", "")),
                str(row.get("root_cause", "")),
                str(row.get("concept_nudge", "")),
            ]
        )

    def match(self, user_error_text: str, error_type: str | None = None, top_k: int = 3) -> List[Dict]:
        if not user_error_text.strip() or self.catalog_df.empty:
            return []

        query_vec = self._vectorizer.transform([user_error_text])
        tfidf_scores = cosine_similarity(query_vec, self._matrix).flatten()

        pattern_scores = self.catalog_df["error_pattern"].fillna("").apply(
            lambda pattern: SequenceMatcher(None, user_error_text.lower(), str(pattern).lower()).ratio()
        )
        combined = 0.75 * tfidf_scores + 0.25 * pattern_scores.to_numpy()

        if error_type:
            exact_type = self.catalog_df["error_type"].str.lower().eq(error_type.lower())
            combined = np.where(exact_type.to_numpy(), combined + 0.15, combined)

        top_indices = np.argsort(combined)[::-1][:top_k]

        matches = []
        for idx in top_indices:
            row = self.catalog_df.iloc[idx].to_dict()
            row["match_score"] = float(combined[idx])
            matches.append(row)
        return matches
