# Admin Guides

## Accessing the Django admin backend

Arches is built on a web framework called Django, which comes with its own administration panel that allows you to create/modify/delete database content through a simple web interface. This is useful for some types of content, like user accounts and management areas, but not for real Arches data which is stored in a more complex manner.

To access the admin pages, go to [hms.fpan.us/admin](https://hms.fpan.us/admin) and login with your admin credentials.

You will see a number of "apps" listed, each with its own set of "models". These models represent tables in the database. The most important apps [HMS](http://localhost:8000/admin/hms/) and [Site Theme](http://localhost:8000/admin/site_theme/).

Using the admin backend should be pretty intuitive, you'll navigate to specific models, like **HMS** > **Scout** and then be able to create, edit, or delete entries in the database.

## Create a new Scout

Scouts are users that can gain access to archaeological sites only through assignment by a database admin (you!). Further, **all scouts have access to any sites that have been parked for Public Access**.

Typically, scouts register on their own through the sign-up form. However, in some cases an admin may need to create one directly through the backend. These are the steps for doing so:

1. Log in as `admin` and go to the admin interface, https://hms.fpan.us/admin
2. Find **Scouts** in the HMS app, and go to **+ Add Scout**
3. In the top section, fill out the following fields:
    - **Password** (doesn't matter what it is, you will need to reset it below)
    - **First Name**
    - **Last Name** 
    - **Email address**
    - **Middle initial**
    - **Username** - Follow this format for consistency: first initial, middle initial, last name. For example, Biff A Hooper would be `bahooper`.
        - It would be best to check ahead that this username doesn't already exist in the system. If it does, add `2`, `3`, etc. (Typically, this is handled via the signup form submission.)
4. In the bottom "Scout Profile" section, fill out any fields you want.
5. Save Scout.
6. Now, go back to the main admin page, and click the **Users** link near the top. This is a list of all user accounts on the site. Find and edit the new user you created.
7. In the edit page, you should see **Invalid password format or unknown hashing algorithm** in the password field. Use the provided link to change the password to something that you can send to the user.
8. Finally, in the edit page, assign the user to both the **Resource Editor** and **Crowdsource Editor** groups, and click **Save**.

## Handling Land Manager accounts

Land Managers are users whose access to Archeaological Sites is determined by a flexble set of rules. Use the Django admin backend to create new Land Managers, or change the permission rules of existing ones.

### Create a new Land Manager

1. Log in as `admin` and go to the admin interface, https://hms.fpan.us/admin
2. Find **Land Mangers** in the HMS app, and go to **+ Add Land Manager**
3. In the **User** field, click **+** to create a new user and set their password
    - Choose a randomized password that can be shared with the land manager by email, and instruct them to change this password when they login for the first time.
4. After the user has been created, click the **&rarr;** button next to its name to open a full edit window for that user.
5. Assign the user to both the **Resource Editor** and **Crowdsource Editor** groups, and then click **Save** to close the window.

That's all! The user's land manager account has been created, but it has no access to any Archaelogical Sites. Now we'll set up the user's permission rules.

### Setting Land Manager permissions

The Land Manager profile contains a few fields that determine which subset of Archaeological Sites will be visible for that user after they have logged in. The first field is the most important, and determines how and if the other fields are necessary:

#### Site access mode

The first two options are pretty straightforward. If you choose one of these two access modes, there is no need to enter anymore information for this land manager:

- **FULL** User gets access to *all* sites.
- **NONE** User *cannot access any* sites.

The other access modes can provide more granular, rule-based access to sites:

- **AREA** User can access sites that fall within any of the Management Areas (parks, forests, etc.) or Management Areas Groups that are added later in the profile.
- **AGENCY** User can access sites that fall within any Management Areas that are managed by the agency that is later defined in the profile.

#### Management agency

If site access mode is **AGENCY**, set the user's agency here. They will now be able to access any sites that fall within areas that are managed by this agency.

This is the proper way to grant a Land Manager access to all sites that are located within any state park (choose: **Florida State Parks**).

#### Individual & grouped areas

If site access mode is **AREA**, then you need to add one or more individual (or grouped) areas to this Land Manager's profile. Doing so will grant the user access to and archaeological sites that fall within the chosen areas. *You can add as many individual or grouped areas as you want.*

This is the proper way to only grant someone access to sites that are located within a specific state park (choose: **Tomoka State Park** from the **Individual areas** list).

Grouped areas are useful if you want to allow Land Managers to access the same subset of management areas. For example, all the state parks within a given district (choose: **SP District 1** from the **Grouped areas** list).

To create a new Management Area Group, click the **+** button next to the **Chosen grouped areas** box, enter a name, and then select all areas to be included. You can now assign that group to this and any other Land Manager profile.



