"""Similarity detection for potential duplicate/related projects."""
import pandas as pd
import numpy as np
from typing import List, Dict, Tuple, Optional
from collections import defaultdict


class SimilarityDetector:
    """
    Detect potentially similar/duplicate projects using text similarity.
    
    For prototype: Uses simple TF-IDF + cosine similarity.
    Can be upgraded to sentence transformers if needed.
    """
    
    def __init__(self, threshold: float = 0.85):
        """
        Initialize similarity detector.
        
        Args:
            threshold: Similarity threshold (0-1). Projects above this
                      are flagged as potentially similar.
        """
        self.threshold = threshold
        self.project_texts = None
        self.similarity_matrix = None
        self.project_count = None
        
    def _get_text_features(self, df: pd.DataFrame) -> np.ndarray:
        """Extract text features from projects."""
        texts = []
        
        for _, row in df.iterrows():
            # Combine relevant text fields
            parts = []
            
            if pd.notna(row.get("state")):
                parts.append(str(row["state"]))
            
            if pd.notna(row.get("constituency")):
                parts.append(str(row["constituency"]))
            
            if pd.notna(row.get("mp_name")):
                parts.append(str(row["mp_name"]))
            
            if pd.notna(row.get("house")):
                parts.append(str(row["house"]))
            
            # For prototype, use available text fields
            # If there's a description field, use it
            desc = row.get("project_description") or row.get("description")
            if pd.notna(desc):
                parts.append(str(desc))
            
            texts.append(" ".join(parts))
        
        return np.array(texts, dtype=object)
    
    def _tokenize(self, text: str) -> set:
        """Simple word tokenization."""
        if not text:
            return set()
        return set(text.lower().split())
    
    def _jaccard_similarity(self, set1: set, set2: set) -> float:
        """Calculate Jaccard similarity between two sets."""
        if not set1 or not set2:
            return 0.0
        intersection = len(set1 & set2)
        union = len(set1 | set2)
        return intersection / union if union > 0 else 0.0
    
    def _ngram_similarity(self, text1: str, text2: str, n: int = 2) -> float:
        """Calculate n-gram similarity between two texts."""
        if not text1 or not text2:
            return 0.0
        
        # Create character n-grams
        ngrams1 = set(text1.lower().replace(" ", "")[i:i+n] 
                     for i in range(len(text1) - n + 1))
        ngrams2 = set(text2.lower().replace(" ", "")[i:i+n] 
                     for i in range(len(text2) - n + 1))
        
        if not ngrams1 or not ngrams2:
            return 0.0
        
        intersection = len(ngrams1 & ngrams2)
        union = len(ngrams1 | ngrams2)
        return intersection / union if union > 0 else 0.0
    
    def _calculate_similarity_matrix(self, texts: np.ndarray) -> np.ndarray:
        """Calculate similarity matrix using Jaccard + n-gram similarity."""
        n = len(texts)
        similarity_matrix = np.zeros((n, n))
        
        for i in range(n):
            for j in range(i, n):
                # Combine Jaccard and n-gram similarity
                set1 = self._tokenize(texts[i])
                set2 = self._tokenize(texts[j])
                
                jaccard = self._jaccard_similarity(set1, set2)
                ngram = self._ngram_similarity(texts[i], texts[j])
                
                # Weighted combination
                similarity = 0.4 * jaccard + 0.6 * ngram
                
                similarity_matrix[i][j] = similarity
                similarity_matrix[j][i] = similarity
        
        return similarity_matrix
    
    def fit(self, df: pd.DataFrame) -> "SimilarityDetector":
        """Prepare similarity detection."""
        self.project_texts = self._get_text_features(df)
        return self
    
    def detect_similar(self, df: pd.DataFrame, 
                       top_n: int = 5) -> Tuple[pd.DataFrame, List[Dict]]:
        """
        Detect similar projects.
        
        Args:
            df: Project dataframe
            top_n: Maximum number of similar projects to return per project
            
        Returns:
            Tuple of (results dataframe, list of similar project pairs)
        """
        if self.project_texts is None:
            self.fit(df)
        
        texts = self._get_text_features(df)
        similarity_matrix = self._calculate_similarity_matrix(texts)
        self.similarity_matrix = similarity_matrix
        self.project_count = len(df)
        
        result = df.copy()
        result["max_similarity"] = 0.0
        result["has_similar"] = False
        
        similar_pairs = []
        
        for i in range(len(df)):
            # Find similar projects (excluding self)
            similarities = similarity_matrix[i].copy()
            similarities[i] = 0  # Exclude self
            
            # Get indices above threshold
            similar_indices = np.where(similarities > self.threshold)[0]
            
            if len(similar_indices) > 0:
                result.iloc[i, result.columns.get_loc("has_similar")] = True
                result.iloc[i, result.columns.get_loc("max_similarity")] = (
                    similarities[similar_indices].max()
                )
                
                # Store similar project IDs
                similar_ids = []
                for idx in similar_indices:
                    similar_ids.append({
                        "project_id": df.iloc[idx].get("project_id", f"P{idx:05d}"),
                        "similarity": round(similarities[idx], 3),
                        "mp_name": df.iloc[idx].get("mp_name", "N/A"),
                        "state": df.iloc[idx].get("state", "N/A"),
                        "house": df.iloc[idx].get("house", "N/A"),
                        "allocated_amount": float(pd.to_numeric(pd.Series([df.iloc[idx].get("allocated_amount", 0)]), errors="coerce").fillna(0).iloc[0]),
                        "matching_features": self._matching_features(df.iloc[i], df.iloc[idx])
                    })
                
                # Sort by similarity
                similar_ids.sort(key=lambda x: x["similarity"], reverse=True)
                similar_ids = similar_ids[:top_n]
                
                for pair in similar_ids:
                    similar_pairs.append({
                        "project_id_1": df.iloc[i].get("project_id", f"P{i:05d}"),
                        "project_id_2": pair["project_id"],
                        "similarity": pair["similarity"],
                        "mp_name_1": df.iloc[i].get("mp_name", "N/A"),
                        "mp_name_2": pair["mp_name"],
                        "state_1": df.iloc[i].get("state", "N/A"),
                        "state_2": pair["state"],
                        "matching_features": pair["matching_features"]
                    })
        
        # Add similarity risk score (0-100)
        result["similarity_risk"] = (result["max_similarity"] * 100).round(2)
        
        return result, similar_pairs
    
    def get_similar_for_project(self, df: pd.DataFrame, 
                                 project_idx: int,
                                 threshold: Optional[float] = None) -> List[Dict]:
        """Get similar projects for a specific project."""
        if self.project_texts is None:
            self.fit(df)
        
        threshold = threshold or self.threshold
        if self.similarity_matrix is None or self.project_count != len(df):
            texts = self._get_text_features(df)
            self.similarity_matrix = self._calculate_similarity_matrix(texts)
            self.project_count = len(df)
        similarity_matrix = self.similarity_matrix
        
        similarities = similarity_matrix[project_idx].copy()
        similarities[project_idx] = 0
        
        similar_indices = np.where(similarities > threshold)[0]
        
        results = []
        for idx in similar_indices:
            results.append({
                "project_id": df.iloc[idx].get("project_id", f"P{idx:05d}"),
                "similarity": round(similarities[idx], 3),
                "mp_name": df.iloc[idx].get("mp_name", "N/A"),
                "state": df.iloc[idx].get("state", "N/A"),
                "allocated_amount": df.iloc[idx].get("allocated_amount", 0),
                "house": df.iloc[idx].get("house", "N/A"),
                "matching_features": self._matching_features(df.iloc[project_idx], df.iloc[idx])
            })
        
        return sorted(results, key=lambda x: x["similarity"], reverse=True)

    @staticmethod
    def _matching_features(row_a: pd.Series, row_b: pd.Series) -> List[str]:
        """List matching metadata fields without implying duplication or fraud."""
        return [col.replace("_", " ").title() for col in ("state", "constituency", "mp_name", "house")
                if pd.notna(row_a.get(col)) and pd.notna(row_b.get(col))
                and str(row_a.get(col)).strip().casefold() == str(row_b.get(col)).strip().casefold()]


def detect_similar_projects(df: pd.DataFrame, 
                            threshold: float = 0.85) -> Tuple[pd.DataFrame, List[Dict]]:
    """Convenience function to detect similar projects."""
    detector = SimilarityDetector(threshold=threshold)
    detector.fit(df)
    return detector.detect_similar(df)


if __name__ == "__main__":
    from mplads.data_loader import load_combined_data
    
    df = load_combined_data()
    detector = SimilarityDetector(threshold=0.85)
    result, pairs = detector.detect_similar(df.head(100))  # Use subset for speed
    
    similar_count = result["has_similar"].sum()
    print(f"Found {similar_count} projects with similar counterparts")
