# tests/bdd/features/orders.feature
Feature: Order Management
  As a restaurant user
  I want to manage food orders
  So that I can track customer requests and prepare their food

  Background:
    Given the system has products with the following details:
      | id | name           | price | category    |
      | 1  | X-Burger       | 15.00 | Burgers     |
      | 2  | Fries          | 8.00  | Sides       |
      | 3  | Soda           | 5.00  | Beverages   |
      | 4  | Double X-Burger| 25.00 | Burgers     |
    And the system has a registered user with CPF "12345678901"

  Scenario: Create a new order successfully
    When a customer creates an order with the following products:
      | product_id |
      | 1          |
      | 2          |
      | 3          |
    Then the order should be created with status "RECEIVED"
    And the total price should be 28.00
    And the order should contain 3 products

  Scenario: Create an order with a registered customer
    When a customer with CPF "12345678901" creates an order with the following products:
      | product_id |
      | 4          |
      | 3          |
    Then the order should be created with status "RECEIVED"
    And the total price should be 30.00
    And the order should contain 2 products
    And the order should be associated with the customer

  Scenario: Update order status
    Given there is an existing order with id "1" and status "RECEIVED"
    When the staff updates the order status to "PREPARING"
    Then the order status should be updated to "PREPARING"

  Scenario: Delete an order
    Given there is an existing order with id "2" and status "RECEIVED"
    When the staff deletes the order
    Then the order should be deleted
    And attempting to retrieve the order should fail

  Scenario: List all orders
    Given there are the following orders in the system:
      | id | status    | total_price | product_ids |
      | 1  | RECEIVED  | 28.00       | 1,2,3       |
      | 2  | PREPARING | 30.00       | 4,3         |
      | 3  | READY     | 15.00       | 1           |
    When the staff requests all orders
    Then 3 orders should be returned
    And the orders should be correctly sorted

  Scenario: Handle product service unavailability
    Given the product service is unavailable
    When a customer creates an order with the following products:
      | product_id |
      | 1          |
    Then an appropriate error message should be shown
    And no order should be created