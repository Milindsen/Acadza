CREATE TABLE `review_audit` (
	`id` text PRIMARY KEY NOT NULL,
	`workspace` text NOT NULL,
	`questionId` text NOT NULL,
	`action` text NOT NULL,
	`actor` text NOT NULL,
	`at` text NOT NULL,
	`note` text NOT NULL,
	`before` text NOT NULL,
	`after` text NOT NULL,
	`proposal` text NOT NULL,
	`version` integer NOT NULL
);
--> statement-breakpoint
CREATE TABLE `review_records` (
	`workspace` text NOT NULL,
	`id` text NOT NULL,
	`content` text NOT NULL,
	`version` integer DEFAULT 0 NOT NULL,
	`status` text DEFAULT 'pending' NOT NULL,
	`nonce` text,
	PRIMARY KEY(`workspace`, `id`)
);
