#ifndef TULIPLM_H
#define TULIPLM_H

void init_model(void);
void learn(const char *text);
void save_model(const char *filename);
void load_model(const char *filename);

#endif