import express, { Request, Response } from "express";
import bodyParser from "body-parser";
import swaggerJsdoc from "swagger-jsdoc";
import swaggerUi from "swagger-ui-express";
import { NotionClientWrapper } from "./notionClient.js";

/**
 * Create an Express REST microservice exposing Notion API operations.
 */

const app = express();
app.use(bodyParser.json());

// Read token from environment variables
const notionToken = process.env.NOTION_API_TOKEN;
if (!notionToken) {
  console.error("ERROR: NOTION_API_TOKEN environment variable is not set.");
  process.exit(1);
}

// Instantiate the Notion client
const notionClient = new NotionClientWrapper(notionToken);

// Swagger definition
const swaggerOptions = {
  definition: {
    openapi: "3.0.0",
    info: {
      title: "Notion API Microservice",
      version: "1.0.0",
      description: "REST microservice for interacting with the Notion API",
    },
    servers: [
      {
        url: "http://localhost:3000",
        description: "Development server",
      },
    ],
  },
  apis: ["./src/index.ts"], // Path to the API docs
};

const swaggerDocs = swaggerJsdoc(swaggerOptions);
app.use("/docs", swaggerUi.serve, swaggerUi.setup(swaggerDocs));

/** 
 * Sample endpoints 
 * 
 * Adjust or add additional endpoints to fit your needs.
 */

/**
 * @openapi
 * /blocks/{block_id}/children:
 *   post:
 *     tags:
 *       - Blocks
 *     summary: Append block children
 *     parameters:
 *       - in: path
 *         name: block_id
 *         required: true
 *         schema:
 *           type: string
 *         description: The ID of the block to append children to
 *     requestBody:
 *       required: true
 *       content:
 *         application/json:
 *           schema:
 *             type: object
 *             properties:
 *               children:
 *                 type: array
 *                 items:
 *                   type: object
 *                 description: Array of block objects to append
 *     responses:
 *       200:
 *         description: Successfully appended blocks
 *       400:
 *         description: Invalid request
 *       401:
 *         description: Unauthorized
 */
app.post("/blocks/:block_id/children", async (req: Request, res: Response) => {
  const { block_id } = req.params;
  const { children } = req.body;
  try {
    const response = await notionClient.appendBlockChildren(block_id, children);
    res.json(response);
  } catch (error: any) {
    res.status(500).json({ error: error.message });
  }
});

/**
 * @openapi
 * /blocks/{block_id}:
 *   get:
 *     tags:
 *       - Blocks
 *     summary: Retrieve a block
 *     parameters:
 *       - in: path
 *         name: block_id
 *         required: true
 *         schema:
 *           type: string
 *         description: The ID of the block to retrieve
 *     responses:
 *       200:
 *         description: Successfully retrieved block
 *       404:
 *         description: Block not found
 *       401:
 *         description: Unauthorized
 */
app.get("/blocks/:block_id", async (req: Request, res: Response) => {
  const { block_id } = req.params;
  try {
    const response = await notionClient.retrieveBlock(block_id);
    res.json(response);
  } catch (error: any) {
    res.status(500).json({ error: error.message });
  }
});

/**
 * @openapi
 * /blocks/{block_id}/children:
 *   get:
 *     tags:
 *       - Blocks
 *     summary: List block children
 *     parameters:
 *       - in: path
 *         name: block_id
 *         required: true
 *         schema:
 *           type: string
 *         description: The ID of the block to list children from
 *       - in: query
 *         name: start_cursor
 *         schema:
 *           type: string
 *         description: Pagination cursor
 *       - in: query
 *         name: page_size
 *         schema:
 *           type: integer
 *         description: Number of results per page
 *     responses:
 *       200:
 *         description: Successfully retrieved block children
 *       401:
 *         description: Unauthorized
 */
app.get("/blocks/:block_id/children", async (req: Request, res: Response) => {
  const { block_id } = req.params;
  const { start_cursor, page_size } = req.query;
  try {
    const response = await notionClient.retrieveBlockChildren(
      block_id,
      start_cursor as string,
      page_size ? Number(page_size) : undefined
    );
    res.json(response);
  } catch (error: any) {
    res.status(500).json({ error: error.message });
  }
});

/**
 * @openapi
 * /blocks/{block_id}:
 *   delete:
 *     tags:
 *       - Blocks
 *     summary: Delete a block
 *     parameters:
 *       - in: path
 *         name: block_id
 *         required: true
 *         schema:
 *           type: string
 *         description: The ID of the block to delete
 *     responses:
 *       200:
 *         description: Successfully deleted block
 *       401:
 *         description: Unauthorized
 */
app.delete("/blocks/:block_id", async (req: Request, res: Response) => {
  const { block_id } = req.params;
  try {
    const response = await notionClient.deleteBlock(block_id);
    res.json(response);
  } catch (error: any) {
    res.status(500).json({ error: error.message });
  }
});

// Pages
/**
 * @openapi
 * /pages/{page_id}:
 *   get:
 *     tags:
 *       - Pages
 *     summary: Retrieve a page
 *     parameters:
 *       - in: path
 *         name: page_id
 *         required: true
 *         schema:
 *           type: string
 *         description: The ID of the page to retrieve
 *     responses:
 *       200:
 *         description: Successfully retrieved page
 *       401:
 *         description: Unauthorized
 */
app.get("/pages/:page_id", async (req: Request, res: Response) => {
  const { page_id } = req.params;
  try {
    const response = await notionClient.retrievePage(page_id);
    res.json(response);
  } catch (error: any) {
    res.status(500).json({ error: error.message });
  }
});

/**
 * @openapi
 * /pages/{page_id}:
 *   patch:
 *     tags:
 *       - Pages
 *     summary: Update page properties
 *     parameters:
 *       - in: path
 *         name: page_id
 *         required: true
 *         schema:
 *           type: string
 *         description: The ID of the page to update
 *     requestBody:
 *       required: true
 *       content:
 *         application/json:
 *           schema:
 *             type: object
 *             properties:
 *               properties:
 *                 type: object
 *                 description: Page properties to update
 *     responses:
 *       200:
 *         description: Successfully updated page
 *       401:
 *         description: Unauthorized
 */
app.patch("/pages/:page_id", async (req: Request, res: Response) => {
  const { page_id } = req.params;
  const { properties } = req.body;
  try {
    const response = await notionClient.updatePageProperties(page_id, properties);
    res.json(response);
  } catch (error: any) {
    res.status(500).json({ error: error.message });
  }
});

/**
 * @openapi
 * /pages:
 *   post:
 *     tags:
 *       - Pages
 *     summary: Create a new page
 *     requestBody:
 *       required: true
 *       content:
 *         application/json:
 *           schema:
 *             type: object
 *             properties:
 *               parent:
 *                 type: object
 *                 required: true
 *                 properties:
 *                   type:
 *                     type: string
 *                     enum: [page_id, database_id]
 *                   page_id:
 *                     type: string
 *               properties:
 *                 type: object
 *                 required: true
 *     responses:
 *       200:
 *         description: Successfully created page
 *       401:
 *         description: Unauthorized
 *       400:
 *         description: Invalid request
 */
app.post("/pages", async (req: Request, res: Response) => {
  const { parent, properties } = req.body;
  try {
    const response = await notionClient.createPage(parent, properties);
    res.json(response);
  } catch (error: any) {
    res.status(500).json({ error: error.message });
  }
});

// Users
/**
 * @openapi
 * /users:
 *   get:
 *     tags:
 *       - Users
 *     summary: List all users
 *     parameters:
 *       - in: query
 *         name: start_cursor
 *         schema:
 *           type: string
 *         description: Pagination cursor
 *       - in: query
 *         name: page_size
 *         schema:
 *           type: integer
 *         description: Number of results per page
 *     responses:
 *       200:
 *         description: Successfully retrieved users
 *       401:
 *         description: Unauthorized
 */
app.get("/users", async (req: Request, res: Response) => {
  const { start_cursor, page_size } = req.query;
  try {
    const response = await notionClient.listAllUsers(
      start_cursor as string,
      page_size ? Number(page_size) : undefined
    );
    res.json(response);
  } catch (error: any) {
    res.status(500).json({ error: error.message });
  }
});

/**
 * @openapi
 * /users/{user_id}:
 *   get:
 *     tags:
 *       - Users
 *     summary: Retrieve a user
 *     parameters:
 *       - in: path
 *         name: user_id
 *         required: true
 *         schema:
 *           type: string
 *         description: The ID of the user to retrieve
 *     responses:
 *       200:
 *         description: Successfully retrieved user
 *       401:
 *         description: Unauthorized
 */
app.get("/users/:user_id", async (req: Request, res: Response) => {
  const { user_id } = req.params;
  try {
    const response = await notionClient.retrieveUser(user_id);
    res.json(response);
  } catch (error: any) {
    res.status(500).json({ error: error.message });
  }
});

/**
 * @openapi
 * /me:
 *   get:
 *     tags:
 *       - Users
 *     summary: Retrieve bot user
 *     responses:
 *       200:
 *         description: Successfully retrieved bot user
 *       401:
 *         description: Unauthorized
 */
app.get("/me", async (_req: Request, res: Response) => {
  try {
    const response = await notionClient.retrieveBotUser();
    res.json(response);
  } catch (error: any) {
    res.status(500).json({ error: error.message });
  }
});

// Databases
/**
 * @openapi
 * /databases:
 *   post:
 *     tags:
 *       - Databases
 *     summary: Create a database
 *     requestBody:
 *       required: true
 *       content:
 *         application/json:
 *           schema:
 *             type: object
 *             properties:
 *               parent:
 *                 type: object
 *                 description: Parent page reference
 *               title:
 *                 type: array
 *                 description: Database title
 *               properties:
 *                 type: object
 *                 description: Database properties schema
 *     responses:
 *       200:
 *         description: Successfully created database
 *       401:
 *         description: Unauthorized
 */
app.post("/databases", async (req: Request, res: Response) => {
  const { parent, title, properties } = req.body;
  try {
    const response = await notionClient.createDatabase(parent, title, properties);
    res.json(response);
  } catch (error: any) {
    res.status(500).json({ error: error.message });
  }
});

/**
 * @openapi
 * /databases/{database_id}/query:
 *   post:
 *     tags:
 *       - Databases
 *     summary: Query a database
 *     parameters:
 *       - in: path
 *         name: database_id
 *         required: true
 *         schema:
 *           type: string
 *         description: The ID of the database to query
 *     requestBody:
 *       required: true
 *       content:
 *         application/json:
 *           schema:
 *             type: object
 *             properties:
 *               filter:
 *                 type: object
 *                 description: Filter criteria
 *               sorts:
 *                 type: array
 *                 description: Sort criteria
 *               start_cursor:
 *                 type: string
 *                 description: Pagination cursor
 *               page_size:
 *                 type: number
 *                 description: Number of results per page
 *     responses:
 *       200:
 *         description: Successfully queried database
 *       400:
 *         description: Invalid request
 *       401:
 *         description: Unauthorized
 */
app.post("/databases/:database_id/query", async (req: Request, res: Response) => {
  const { database_id } = req.params;
  const { filter, sorts, start_cursor, page_size } = req.body;
  try {
    const response = await notionClient.queryDatabase(
      database_id,
      filter,
      sorts,
      start_cursor,
      page_size
    );
    res.json(response);
  } catch (error: any) {
    res.status(500).json({ error: error.message });
  }
});

/**
 * @openapi
 * /databases/{database_id}:
 *   get:
 *     tags:
 *       - Databases
 *     summary: Retrieve a database
 *     parameters:
 *       - in: path
 *         name: database_id
 *         required: true
 *         schema:
 *           type: string
 *         description: The ID of the database to retrieve
 *     responses:
 *       200:
 *         description: Successfully retrieved database
 *       401:
 *         description: Unauthorized
 */
app.get("/databases/:database_id", async (req: Request, res: Response) => {
  const { database_id } = req.params;
  try {
    const response = await notionClient.retrieveDatabase(database_id);
    res.json(response);
  } catch (error: any) {
    res.status(500).json({ error: error.message });
  }
});

/**
 * @openapi
 * /databases/{database_id}:
 *   patch:
 *     tags:
 *       - Databases
 *     summary: Update database
 *     parameters:
 *       - in: path
 *         name: database_id
 *         required: true
 *         schema:
 *           type: string
 *         description: The ID of the database to update
 *     requestBody:
 *       required: true
 *       content:
 *         application/json:
 *           schema:
 *             type: object
 *             properties:
 *               title:
 *                 type: array
 *                 description: Database title
 *               description:
 *                 type: array
 *                 description: Database description
 *               properties:
 *                 type: object
 *                 description: Database properties schema
 *     responses:
 *       200:
 *         description: Successfully updated database
 *       401:
 *         description: Unauthorized
 */
app.patch("/databases/:database_id", async (req: Request, res: Response) => {
  const { database_id } = req.params;
  const { title, description, properties } = req.body;
  try {
    const response = await notionClient.updateDatabase(
      database_id,
      title,
      description,
      properties
    );
    res.json(response);
  } catch (error: any) {
    res.status(500).json({ error: error.message });
  }
});

/**
 * @openapi
 * /databases/{database_id}/items:
 *   post:
 *     tags:
 *       - Databases
 *     summary: Create database item
 *     parameters:
 *       - in: path
 *         name: database_id
 *         required: true
 *         schema:
 *           type: string
 *         description: The ID of the database to create item in
 *     requestBody:
 *       required: true
 *       content:
 *         application/json:
 *           schema:
 *             type: object
 *             properties:
 *               properties:
 *                 type: object
 *                 description: Properties of the new item
 *     responses:
 *       200:
 *         description: Successfully created database item
 *       401:
 *         description: Unauthorized
 */
app.post("/databases/:database_id/items", async (req: Request, res: Response) => {
  const { database_id } = req.params;
  const { properties } = req.body;
  try {
    const response = await notionClient.createDatabaseItem(database_id, properties);
    res.json(response);
  } catch (error: any) {
    res.status(500).json({ error: error.message });
  }
});

// Comments
/**
 * @openapi
 * /comments:
 *   post:
 *     tags:
 *       - Comments
 *     summary: Create a comment
 *     requestBody:
 *       required: true
 *       content:
 *         application/json:
 *           schema:
 *             type: object
 *             properties:
 *               parent:
 *                 type: object
 *                 description: Parent page reference
 *               discussion_id:
 *                 type: string
 *                 description: Discussion ID
 *               rich_text:
 *                 type: array
 *                 description: Comment content
 *     responses:
 *       200:
 *         description: Successfully created comment
 *       400:
 *         description: Invalid request
 *       401:
 *         description: Unauthorized
 */
app.post("/comments", async (req: Request, res: Response) => {
  const { parent, discussion_id, rich_text } = req.body;
  try {
    // At least one must exist: parent.page_id or discussion_id
    if (!parent && !discussion_id) {
      return res.status(400).json({
        error: "You must supply either parent.page_id or discussion_id",
      });
    }
    const response = await notionClient.createComment(parent, discussion_id, rich_text);
    res.json(response);
  } catch (error: any) {
    res.status(500).json({ error: error.message });
  }
});

/**
 * @openapi
 * /comments:
 *   get:
 *     tags:
 *       - Comments
 *     summary: Retrieve comments
 *     parameters:
 *       - in: query
 *         name: block_id
 *         required: true
 *         schema:
 *           type: string
 *         description: The ID of the block to retrieve comments from
 *       - in: query
 *         name: start_cursor
 *         schema:
 *           type: string
 *         description: Pagination cursor
 *       - in: query
 *         name: page_size
 *         schema:
 *           type: integer
 *         description: Number of results per page
 *     responses:
 *       200:
 *         description: Successfully retrieved comments
 *       400:
 *         description: Invalid request
 *       401:
 *         description: Unauthorized
 */
app.get("/comments", async (req: Request, res: Response) => {
  const { block_id, start_cursor, page_size } = req.query;
  if (!block_id) {
    return res
      .status(400)
      .json({ error: "You must supply block_id as a query parameter" });
  }
  try {
    const response = await notionClient.retrieveComments(
      block_id as string,
      start_cursor as string,
      page_size ? Number(page_size) : undefined
    );
    res.json(response);
  } catch (error: any) {
    res.status(500).json({ error: error.message });
  }
});

/**
 * @openapi
 * /search:
 *   post:
 *     tags:
 *       - Search
 *     summary: Search Notion
 *     requestBody:
 *       required: true
 *       content:
 *         application/json:
 *           schema:
 *             type: object
 *             properties:
 *               query:
 *                 type: string
 *                 description: Search query string
 *               filter:
 *                 type: object
 *                 description: Filter criteria
 *               sort:
 *                 type: object
 *                 description: Sort criteria
 *               start_cursor:
 *                 type: string
 *                 description: Pagination cursor
 *               page_size:
 *                 type: number
 *                 description: Number of results per page
 *     responses:
 *       200:
 *         description: Search results
 *       400:
 *         description: Invalid request
 *       401:
 *         description: Unauthorized
 */
app.post("/search", async (req: Request, res: Response) => {
  const { query, filter, sort, start_cursor, page_size } = req.body;
  try {
    const response = await notionClient.search(
      query,
      filter,
      sort,
      start_cursor,
      page_size
    );
    res.json(response);
  } catch (error: any) {
    res.status(500).json({ error: error.message });
  }
});

// Start the server
const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`Notion microservice running on http://localhost:${PORT}`);
});

