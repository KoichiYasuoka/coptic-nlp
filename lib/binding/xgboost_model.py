from __future__ import division

import numpy as np
from xgboost import XGBClassifier, XGBRegressor

from .tokenizer import Tokenizer
from .featurizer import Featurizer
from .postprocessor import Postprocessor


class XGBoostBindingModel:
	def __init__(
		self,
		ignore_chars=[],
		n_groups_left=1,
		n_groups_right=2,
		gold_token_separator="_",
		orig_token_separator=" ",
		binding_freq_file_path=None,
		ngram_binding_freq_file_path=None,
		pos_file_path=None,
		group_freq_file_path=None,
		# for the model
		n_estimators=150,
		max_depth=18,
		eta=0.08,
		gamma=0.18,
		colsample_bytree=0.6,
		subsample=0.9,
		min_child_weight=2,
	):
		self._tokens = []
		self._tokenizer = Tokenizer(
			gold_token_separator=gold_token_separator,
			orig_token_separator=orig_token_separator,
			ignore_chars=ignore_chars,
			lowercase=True,
			normalize=True
		)
		self._featurizer = Featurizer(
			# seps might occur in tokens, also add them to the ignore list
			n_groups_left,
			n_groups_right,
			ignore_chars=ignore_chars + [orig_token_separator, gold_token_separator],
			orig_token_separator=" ",
			binding_freq_file_path=binding_freq_file_path,
			ngram_binding_freq_file_path=ngram_binding_freq_file_path,
			pos_file_path=pos_file_path,
			group_freq_file_path=group_freq_file_path,
			encoder='label'
		)
		self._postprocessor = Postprocessor(separator=gold_token_separator)

		# cf: https://xgboost.readthedocs.io/en/latest/python/python_api.html#xgboost.XGBClassifier
		self._m = XGBClassifier(
			nthread=-1,
			n_estimators=n_estimators,
			colsample_bytree=colsample_bytree,
			max_depth=max_depth,
			eta=eta,
			gamma=gamma,
			subsample=subsample,
			min_child_weight=min_child_weight,
		)

	def _build_feature_matrix(self, text, orig_text=None, training=False):
		"""Prepare X matrix for input to the model. text is gold if orig_text is
		not none, else it is orig"""

		tokens = self._tokenizer.tokenize(text, orig=orig_text)
		self._tokens = tokens
		X = np.array(
			self._featurizer
				.load_tokens(tokens, training=training)
				.add_group_count()
				.add_combined_token_group_count()
				#.add_morph_bound_count()
				#.add_morph_not_bound_count()
				#.add_morph_prob_bound()
				#.add_ngram_bound_count(left=0, right=0)
				#.add_ngram_not_bound_count(left=0, right=0)
				#.add_ngram_prob_bound(left=0, right=0)
				#.add_combined_token_morph_bound_count()
				#.add_combined_token_morph_not_bound_count()
				#.add_combined_token_morph_prob_bound()
				.add_length(left=1, right=2)
				.add_pos(left=1, right=2)
				#.add_is_prep(left=0, right=1)
				.add_first_letter(left=0, right=1)
				.add_last_letter(left=1, right=0)
				.add_right_substr_pos(left=1, right=0)
				.add_left_substr_pos(left=0, right=1)
				.add_auto_norm_response(left=1, right=0)
				.add_all_punct(left=0, right=1)
				#.add_any_punct(left=1, right=1)
				.features()
		)

		return X

	def _build_label_vector(self):
		vec = np.array(
			self._featurizer
				.load_tokens(self._tokens)
				.labels()
		)
		return vec

	def train(self, gold_text, orig_text=None):
		X = self._build_feature_matrix(gold_text, orig_text=orig_text, training=True)
		y = self._build_label_vector()
		self._m.fit(X, y)

	def predict(self, orig_text, return_type="text"):
		X = self._build_feature_matrix(orig_text)
		output = self._m.predict(X).tolist()
		if return_type == "text":
			output = self._postprocessor.insert_separators(self._tokens, output)
		return output





