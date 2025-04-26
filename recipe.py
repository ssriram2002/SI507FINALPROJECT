import requests
import re
import json
import os
import networkx as nx

class Recipes:
    """
    A class to manage and analyze recipes and the ingredients.

    Attributes
    ----------
    recipes : list of recipies
    ingredient: each ingredient
    myRecipes_graph: co-occurrence network of ingredients graph
    """

    def __init__(self,cacheFile = None):
        """
        Initializes the Recipe class without any recipes.
        assign recipes attribute to an empty list
        
        Parameters
        ----------
         cacheFile: str, optional
            name of cache file to load data from, if None initialized without data
    
         Return
         ----------
            nothing
        """
        if cacheFile is not None:
            successful_load = self.loadCache(cacheFile)
            if not successful_load:
                self.recipes = []
        else:
            self.recipes = []

        self.ingredient_list = {}


    def fetchRecipe(self):

        """
        Fetches information about 100 recipes from Spoonacular API. 
        Prints error messages for if the number of API calls have reached for the day, 
        and the response code for all other errors  

        Note
        ----------
        The method fetches data from "https://api.spoonacular.com/recipes/random"
        
        Return
        ----------
            The 100 recipies data in json format. 
        """

            # Retry the request until a valid response (status code 200)
        apiKey= "84054af1abdd4b06a0146895a8f436c0"
        url= "https://api.spoonacular.com/recipes/random"
        params = { 'apiKey': apiKey, 'number': 100, 'includeNutrition': False }
        response = requests.get(url, params=params)

        if response.status_code == 200:
            recipe_data_formatted = response.json()
            return recipe_data_formatted
        elif response.status_code ==402:
            print ("You have reached api call quota for the day")
        else:
            print("response code is: ", response.status_code)


    def loadCache(self, fileName):
        """
        Loads recipe data from a cache JSON file if it exists. 
        If it fails to load data in cache File it gives error message. 

        Parameters
        ----------
        fileName : str
            The name of the file from which to load the recipe data.

        Returns
        -------
        bool
            True if the data was successfully loaded, False otherwise.
        """
        if not os.path.exists(fileName):
            return False

        try:
            with open(fileName, 'r') as f:
                recipe_data = json.load(f)

            self.recipes = recipe_data
            print(f"Successfully loaded {len(self.recipes)} recipes from {fileName}.")
            return True

        except (IOError, json.JSONDecodeError, TypeError) as e:
            print(f"Error loading cache: {e}")
            return False


    def build_ingredient_list(self):
        """
        Creates a dictionary mapping unique ingredient names to their IDs,
        avoiding duplicate ingredient names (case-insensitive).
        """
        seen_names = set()
        cleaned_ingredients = {}

        for recipe in self.recipes:
            for ingredient in recipe['extendedIngredients']:
                ingredient_id = ingredient['id']
                ingredient_name = ingredient['name'].strip().lower()
                cleaned_name = self.clean_ingredient_name(ingredient_name)


                if cleaned_name not in seen_names:
                    seen_names.add(cleaned_name)
                    cleaned_ingredients[ingredient_id] = ingredient['name']

        self.ingredient_list = dict(sorted(cleaned_ingredients.items(), key=lambda item: item[1].lower()))
        print(f"Built ingredient list with {len(self.ingredient_list)} unique items.")


    def clean_ingredient_name(self, ingredient):
        """
        Cleans the ingredient name by removing measurements, numbers, and extra terms
        like "tsp", "tbsp", "oz", etc.

        Parameters
        ----------
        self
        str: ingredient name

        Returns
        ----------
        str: cleaned ingredient name
        """
        cleaned_name = re.sub(r'\d+|tsp|tbsp|oz|g|kg|lbs|cm|inch|cup|tablespoon|teaspoon|pound|grams|milliliter|liter|serving|to|and|from|by|\\+|\\-|\(|\)', '', ingredient)
        cleaned_name = cleaned_name.strip()
        return cleaned_name


    def get_substitutes(self, ingredient_name):

        """
        Fetches substitues of ingredient from the Spoonacular API. 
        Prints out the substutes for the ingredients. 
        If there are no substitues it prints could not find any substitutes. 

        Parameters
        ----------
        self
        str: ingredient name

        Note
        ----
        The method fetches data from ""https://api.spoonacular.com/food/ingredients/substitutes

        Returns
        ----------
        nothing
        """

            # Retry the request until a valid response (status code 200)
        apiKey= "84054af1abdd4b06a0146895a8f436c0"
        url= "https://api.spoonacular.com/food/ingredients/substitutes"
        params = { 'apiKey': apiKey, 'ingredientName': ingredient_name}
        response = requests.get(url, params=params)

        if response.status_code == 200:
            ingredient_sub_formatted = response.json()
            if ingredient_sub_formatted['message']== 'Could not find any substitutes for that ingredient.':
                print("This ingredient does not have any substitutes.")
            else:
                substitues= ingredient_sub_formatted['substitutes']
                print(f"The substitues for '{ingredient_name}' are: ")
                for sub in substitues:
                    print(sub)
        elif response.status_code ==402:
            print ("You have reached api call quota for the day")
        else:
            print("response code is: ", response.status_code)


    def cacheData(self, fileName):
        """
        Creates a new cache file or updates current cache file with more recipes.
        Checks for duplicate recipes and caps cache file at 1099 recipes.

        Parameters
        ----------
        filename : str
            The name of the file where the recipe data will be saved.
        
        Returns
        ----------
        nothing
        """

        if not os.path.exists(fileName):
            #checks to see if the cache file has been created if not creates new file and dumps all data into it
            with open(fileName, 'w') as f:
                recipe_data_formatted= self.fetchRecipe()
                json.dump(recipe_data_formatted["recipes"],f, indent=4)
            return
        with open(fileName, 'r') as f:
            try:
                existing_data= json.load(f)
                #checks to see if the cache file is empty
            except:
                existing_data= []
        existing_data_size= len(existing_data)
        recipe_data_formatted= self.fetchRecipe()
        for recipe in recipe_data_formatted['recipes']:
            if existing_data_size<=1000:
                if recipe['id'] not in existing_data:
                    #json.dump(recipe, f, indent=4)
                    #temp_data.append(recipe)
                    existing_data.append(recipe)
                    print("Recipe not in list")
                else:
                    print("Recipe already in list")
            else:
                print("There are 500 recipes")
                break
        with open(fileName, 'w') as f:
            json.dump(existing_data, f, indent=4)


    def build_ingredient_network(self):
        """
        Builds a co-occurrence network of ingredients from the recipe dataset.
        Each ingredient is represented as a node, 
        and an edge is created between any two ingredients that appear in the same recipe. 
        The weight of the edge represents how often the two ingredients co-occur across all recipes.       

        Parameters
        ----------
         self

        Returns
        ----------
        nothing
        """

        self.myRecipes_graph = nx.Graph()

        for recipe in self.recipes:
            ingredients = recipe['extendedIngredients']

            for ingredient in ingredients:
                ingredient_id = ingredient['id']
                if not self.myRecipes_graph.has_node(ingredient_id):
                    self.myRecipes_graph.add_node(ingredient_id, name=ingredient['name'])
                for other_ingredient in ingredients:
                    if ingredient != other_ingredient:
                        other_ingredient_id = other_ingredient['id']
                        if not self.myRecipes_graph.has_edge(ingredient_id, other_ingredient_id):
                            self.myRecipes_graph.add_edge(ingredient_id, other_ingredient_id, weight=1)
                        else:
                            self.myRecipes_graph[ingredient_id][other_ingredient_id]['weight'] += 1



    def get_ingredient_recommendations(self, ingredient_name, top_n=5):
        """
        Given an ingredient name, recommends other ingredients that co-occur frequently with it in the ingredient network.
        Uses ingredinet dictionary to find ingredients with the entered string in it and prints the options in an ordered list. 
        User choices ingredient and then is given ingredient pairing reccomendation. 
        
        Parameters:
        -----------
        ingredient_name : str
            The name (or partial name) of the ingredient for which recommendations are made.
        top_n : int
            The number of recommended ingredients to return.

        Returns:
        --------
        list
            A list of recommended ingredient names with co-occurrence frequency.
        """

        matches = [(id, name) for id, name in self.ingredient_list.items() if ingredient_name.lower() in name.lower()]

        if not matches:
            print(f"No ingredient found matching '{ingredient_name}'.")
            return []

        if len(matches) > 1:
            print(f"Multiple matches found for '{ingredient_name}':")
            for i, (id, name) in enumerate(matches):
                print(f"{i+1}. {name} (ID: {id})")
        else:
            ingredient_id, matched_name = matches[0]

        while True:
            try:
                choice = int(input("Enter the number of the ingredient you meant: "))
                if 1 <= choice <= len(matches):
                    ingredient_id, matched_name = matches[choice - 1]
                    break
                else:
                    print("Invalid choice. Please enter a number from the list.")
            except ValueError:
                print("Please enter a valid number.")

        neighbors = list(self.myRecipes_graph.neighbors(ingredient_id))
        if not neighbors:
            print(f"No neighbors found for ingredient: {matched_name} (ID: {ingredient_id}).")
            return []

        recommendations = sorted(
            [(self.ingredient_list.get(n, 'Unknown'), self.myRecipes_graph[ingredient_id][n]['weight']) for n in neighbors],
            key=lambda x: x[1],
            reverse=True
        )

        print(f"Recommendations to go with ingredient '{matched_name}' (ID: {ingredient_id}):")
        for name, weight in recommendations[:top_n]:
            print(f"- {name} (co-occurs {weight} times)")

        return recommendations[:top_n]


    def get_ingredient_info(self,ingredient_name):
        """
        Given an ingredient name, fetches data from Spoonacular about the ingredinet. 
        Uses ingredient dictionary to find ingredinets with the entered string in it and prints the options in an ordered list. 
        Prints the price and grocery ailse the ingredient is found in. 
        
        Note:
        -----------
        Uses endpoint: https://api.spoonacular.com/food/ingredients/{ingredient_id}/information

        Parameters:
        -----------
        ingredient_name : str
            The name (or partial name) of the ingredient for which recommendations are made.

        Returns:
        --------
            nothing
        """

        matches = [(id, name) for id, name in self.ingredient_list.items() if ingredient_name.lower() in name.lower()]

        if not matches:
            print(f"No ingredient found matching '{ingredient_name}'.")
            return []

        if len(matches) > 1:
            print(f"Multiple matches found for '{ingredient_name}':")
            for i, (id, name) in enumerate(matches):
                print(f"{i+1}. {name} (ID: {id})")
        else:
            ingredient_id, matched_name = matches[0]

        while True:
            try:
                choice = int(input("Enter the number of the ingredient you meant: "))
                if 1 <= choice <= len(matches):
                    ingredient_id = matches[choice - 1]
                    break
                else:
                    print("Invalid choice. Please enter a number from the list.")
            except ValueError:
                print("Please enter a valid number.")


        apiKey= "84054af1abdd4b06a0146895a8f436c0"
        url= f"https://api.spoonacular.com/food/ingredients/{ingredient_id}/information"
        params = { 'apiKey': apiKey}
        response = requests.get(url, params=params)
        ingredient_info_formatted = response.json()
        #print(ingredient_info_formatted)

        aisle= ingredient_info_formatted.get('aisle', None)
        price_info= ingredient_info_formatted.get('estimatedCost', None)

        aisle_message = "No information on the aisle."
        estimated_price_message = "No information on the estimated cost."

        if aisle:
            aisle_message = aisle
        if price_info and price_info.get('unit') == 'US Cents':
            estimated_price = price_info['value'] / 100
            estimated_price_message = f"${estimated_price:.2f}"
        print(f"{matched_name}' can be found in ailse: '{aisle_message}")
        print(f"The estimated price for '{matched_name}' is: '{estimated_price_message}")


    def get_most_connected_ingredient(self):
        """
        Finds the ingredient with the most unique co-occurring ingredient connections across all recipes.

        """
        co_occurrence_graph = {}

        for recipe in self.recipes:
            ingredients = [ingredient['name'].strip().lower() for ingredient in recipe['extendedIngredients']]
            for i, ingredient in enumerate(ingredients):
                if ingredient not in co_occurrence_graph:
                    co_occurrence_graph[ingredient] = set()

                for j in range(len(ingredients)):
                    if i != j:
                        co_occurrence_graph[ingredient].add(ingredients[j])

        most_connected = max(co_occurrence_graph.items(), key=lambda x: len(x[1]))

        print(f"Most connected ingredient: '{most_connected[0]}' with {len(most_connected[1])} unique connections.")
        return most_connected[0], len(most_connected[1])


def main():
    """
    Welcome user to Cooking helper, and asks user what they need help with.
    Runs coresponding function, and asks if the user wants more help after printing the answer. 
    If they need more help runs game again, if not exits game. 
    """
    myRecipes = Recipes(cacheFile='recipeCache1.json')
    myRecipes.build_ingredient_network()
    myRecipes.build_ingredient_list()

    question_options= ['Reccomendations for Ingredient pairings ',
                       'Ingredient Substitues',
                       'Find out what the most connected ingredient is!!',
                       'Ingredient Price and Ailse Informtion']
    print("Welcome to the Cooking Helper! Let me know what information you want from the options below: ")
    while True:
        print("\nWhat information would you like?")
        for i, option in enumerate(question_options):
            print(f"{i+1}. {option}")
        while True:
            try:
                choice = int(input("\nEnter the number of the option you want: "))
                if 1 <= choice <= len(question_options):
                    break
                else:
                    print("Invalid choice. Please enter a number from the list.")
            except ValueError:
                print("Please enter a valid number.")
        
        if choice == 1:
            ingredient_name = input("What is the name of the ingredient you want to get pairing recommendations for? ").strip().lower()
            myRecipes.get_ingredient_recommendations(ingredient_name)

        elif choice == 2:
            ingredient_name = input("What is the name of the ingredient you want substitutions for? ").strip().lower()
            myRecipes.get_substitutes(ingredient_name)

        elif choice == 3:
            myRecipes.get_most_connected_ingredient()

        elif choice == 4:
            ingredient_name = input("Enter the name of the ingredient to get price and aisle info: ").strip().lower()
            myRecipes.get_ingredient_info(ingredient_name)

        more_help_answ= input("Do you need more help (yes/no? ").strip().lower()
        if more_help_answ not in ['yes', 'y', 'sure', 'yeah', 'yup']:
            print("\nOkay, happy cooking!")
            break


    #WORKS!!! myRecipes.fetchRecipe()
    # WORKS!!! myRecipes.cacheData('recipeCache1.json')
    #userinput= input("Which ingredient would you like to get recommendations for? Please enter the name of the ingredient: ")
    #myRecipes.build_ingredient_network()
    #myRecipes.build_ingredient_list()
    #myRecipes.get_ingredient_recommendations(userinput)
    #myRecipes.get_ingredient_info('tuna')
    #myRecipes.fetchSubtitute('butter')
    #myRecipes.get_most_connected_ingredient()

  


main()



