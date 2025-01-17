from random import randrange
from scipy.ndimage.interpolation import rotate

import numpy as np
import cv2


class DoubleQLearning:
    def __init__(self):
        self.alpha = 1
        self.gamma = 0
        self.angle1 = 90
        self.angle2 = 180
        self.angle3 = 12.5
        self.angle4 = -12.5
        self.M_translation = np.float32([[1, 0, 15], [0, 1, 15]])
        self.M_translation_2 = np.float32([[1, 0, -15], [0, 1, -15]])

        self.action = None
        self.rand_Q_table = 0

        self.actions = dict([(0, self.action_rotate_1), (1, self.action_rotate_2), (2, self.diagonal_translation)])

        self.r = 0
        self.episode = 0
        self.maxIter = 10
        self.max_q_estimates = []
        self.rewards = []
        self.cum_rewards = []
        self.cum_rewards_all_images = []
        self.max_q_estimates_all_images = []

        self.total = [0, 0, 0]

        # Initialize QA,QB,s
        self.states = [0, 1]
        self.tableQ_A = np.zeros((len(self.states), len(self.actions)))
        self.tableQ_B = np.zeros((len(self.states), len(self.actions)))
        self.average_q_table = np.zeros((len(self.states), len(self.actions)))

    def action_rotate_1(self, picture):
        return rotate(picture, self.angle1, reshape=False)

    def action_rotate_2(self, picture):
        return rotate(picture, self.angle2, reshape=False)

    def action_rotate_3(self, picture):
        return rotate(picture, self.angle3, reshape=False)

    def action_rotate_4(self, picture):
        return rotate(picture, self.angle4, reshape=False)

    def diagonal_translation(self, picture):
        rows, cols = picture.shape[:2]
        translated = cv2.warpAffine(picture, self.M_translation, (cols, rows))
        return np.array(translated)

    def diagonal_translation_2(self, picture):
        rows, cols = picture.shape[:2]
        translated = cv2.warpAffine(picture, self.M_translation_2, (cols, rows))
        return np.array(translated)

    def selectAction(self):
        return randrange(len(self.actions))

    def epsilon_greedy_selection(self, eps):
        p = np.random.random()
        if p < eps:
            rand_action = np.random.choice(len(self.actions))
            print(f'Rand action: {rand_action}')
            return int(rand_action)
        else:
            self.average_q_table = np.mean([self.tableQ_A, self.tableQ_B], axis=0)
            print(self.average_q_table)
            total = np.sum(self.average_q_table, axis=0)
            print(f'Total: {total}')
            best_action = np.argmax(total)
            print(f'Best action: {best_action}')
            return int(best_action)

    def selectAction(self):
        return randrange(len(self.actions))

    def apply_action(self, action, img):
        return self.actions[action](img)

    def get_features_metric(self, features):
        return np.std(features)

    def get_reward(self, m1, m2):
        return 1 if m2 > m1 else -1

    def define_state(self, reward):
        print("State chosen: " + str(0 if reward > 0 else 1))
        return 0 if reward > 0 else 1

    def update_tableQ(self, state, action, reward):
        print(
            f'{self.tableQ[state][action]} + {self.alpha} * ({reward} + {self.gamma} * {max(self.tableQ[state])}) - {self.tableQ[state][action]} ')
        self.tableQ[state][action] = self.tableQ[state][action] + (
                self.alpha * (reward + self.gamma * max(self.tableQ[state]) - self.tableQ[state][action]))
        print(f'New Table Q(s,a) value: {self.tableQ[state][action]}')

    def update_tableQ_A(self, state, action, reward):
        a_star = int(np.argmax(self.tableQ_A[state]))
        # print(f'{self.tableQ_A[state][action]} = {self.tableQ_A[state][action]} + {self.alpha} * ({reward} + ({self.gamma} * {self.tableQ_B[state][a_star]}) - {self.tableQ_A[state][action]})')
        self.tableQ_A[state][action] = self.tableQ_A[state][action] + self.alpha * (reward + (self.gamma * self.tableQ_B[state][a_star]) - self.tableQ_A[state][action])
        # print(f'New Table A Q(s,a) value: {self.tableQ_A[state][action]}')

    def update_TableQ_B(self, state, action, reward):
        b_star = int(np.argmax(self.tableQ_B[state]))
        # print(f'{self.tableQ_B[state][action]} = {self.tableQ_B[state][action]} + {self.alpha} * ({reward} + ({self.gamma} * {self.tableQ_A[state][b_star]}) - {self.tableQ_B[state][action]})')
        self.tableQ_B[state][action] = self.tableQ_B[state][action] + self.alpha * (reward + (self.gamma * self.tableQ_A[state][b_star]) - self.tableQ_B[state][action])
        # print(f'New Table B Q(s,a) value: {self.tableQ_B[state][action]}')

    def get_best_max_Q_values_one_img(self):
        array_totals = [np.sum(arr) for arr in self.max_q_estimates_all_images]
        highest_total_index = np.argmax(array_totals)
        best_q_estimates_list = self.max_q_estimates_all_images[highest_total_index]

        return best_q_estimates_list

    def get_best_max_cum_r_one_img(self):
        array_totals = [np.sum(arr) for arr in self.cum_rewards_all_images]
        highest_total_index = np.argmax(array_totals)
        best_cum_r_list = self.cum_rewards_all_images[highest_total_index]

        return best_cum_r_list

    def perform_iterative_Q_learning(self, cnn, img, classes, action_selection_strategy, alpha, gamma):
        print(f'selected strategy: {action_selection_strategy}')
        self.alpha = alpha
        self.gamma = gamma

        print(f'Reset here')
        self.tableQ_A = np.zeros((len(self.states), len(self.actions)))
        self.tableQ_B = np.zeros((len(self.states), len(self.actions)))
        self.average_q_table = np.zeros((len(self.states), len(self.actions)))
        self.rewards = []
        self.cum_rewards = []
        self.max_q_estimates = []

        # Make sure this is in every class
        # --------------------------------
        eps = 1.0
        decay_index = 0
        # ---------------------------------

        img_features = cnn.get_output_base_model(
            img)  # The output activation function of the last layer (original image)
        m1 = self.get_features_metric(img_features)  # The std deviation of img_features (original image)
        print("m1: " + str(m1))

        # Run for (3 actions * 20 = 60 iterations) or until human stops
        for i in range(self.maxIter):
            self.max_q_estimates.append(np.max(self.average_q_table))
            print(f'Max q value list updated: {str(self.max_q_estimates)}')

            self.episode = self.episode + 1
            print(f'Episode: {self.episode}')

            if action_selection_strategy == 'random':
                # ---------------------------------------------
                # Random strategy
                self.action = self.selectAction()
                # ---------------------------------------------
            elif action_selection_strategy == 'harmonic-sequence-e-decay':
                # ----------------------------------------------------
                # Epsilon strategy with harmonic sequence decay part 1
                self.action = self.epsilon_greedy_selection(eps)
                # ----------------------------------------------------
            elif action_selection_strategy == 'one-shot-e-decay':
                # ----------------------------------------------
                # Epsilon strategy with one shot decay part 1
                self.action = self.epsilon_greedy_selection(eps)
                # ----------------------------------------------

            modified_img = self.apply_action(self.action, img)
            modified_img_features = cnn.get_output_base_model(
                modified_img)  # The output activation function of the last layer (modified image)
            m2 = self.get_features_metric(modified_img_features)  # The std deviation of img_features (modified image)
            print(m2)
            self.r = self.get_reward(m1, m2)  # Calculate reward using m2-m1, (m2 > m1 for positive reward) (new std_dev must be higher for positive reward)
            self.rewards.append(self.r)

            state = self.define_state(self.r)  # Choose a state in the Q-Table, state 0 is reward > 0
            # Choose Q-table and update
            rand_Q_table = np.random.randint(2)
            if rand_Q_table == 0:
                self.update_tableQ_A(state, self.action, self.r)
            if rand_Q_table == 1:
                self.update_TableQ_B(state, self.action, self.r)

            if action_selection_strategy == 'harmonic-sequence-e-decay' and self.r == 1:
                eps = 1 / (decay_index + 1) ** 2
                decay_index = decay_index + 1
            elif action_selection_strategy == 'one-shot-e-decay' and self.r != 1:
                eps = 0

        self.cum_rewards = np.cumsum(self.rewards)
        self.cum_rewards_all_images.append(self.cum_rewards)
        self.max_q_estimates_all_images.append(self.max_q_estimates)

    def choose_optimal_action(self):
        total = np.sum(self.average_q_table, axis=0)
        best_action = np.argmax(total)
        print(f'Optimal action: {best_action}')
        return best_action
